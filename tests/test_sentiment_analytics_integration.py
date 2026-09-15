"""Offline acceptance checks for the combined sentiment and analytics features."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.agent.sentiment import score_sentiment
from src.analytics.agreement import compute_discussion_agreement, compute_round_agreement
from src.analytics.influence import compute_agent_influence
from src.analytics.models import AgentStancePoint, OpinionTrajectoryResult
from src.analytics.run_analytics import parse_args, run_analytics_pipeline
from src.analytics.stance import compute_opinion_trajectories, extract_numeric_stance, score_snapshots_with_llm, score_snapshot_with_embeddings
from src.discussion.persistence import load_discussion
from test_week3_reliability import ScriptedLLM, source, runner


@pytest.mark.parametrize('text,label', [('I love this brilliant performance!', 'positive'), ('This is a horrible disaster.', 'negative'), ('', 'neutral'), (None, 'neutral')])
def test_sentiment_labels(text, label):
    value, actual = score_sentiment(text)
    assert actual == label
    assert -1 <= value <= 1


def test_source_list_does_not_change_sentiment():
    text = 'A brilliant performance.'
    assert score_sentiment(text) == score_sentiment(text + '\nSOURCES USED:\nHorrible disgusting disaster')


def test_full_discussion_sentiment_and_analytics_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'present-but-must-not-be-used')
    monkeypatch.setattr(runner, 'OpenAICompatibleLLM', lambda: ScriptedLLM())
    monkeypatch.setattr(runner, 'RAGRetrieval', lambda **kwargs: SimpleNamespace(retrieve=lambda query: [source()]))
    assert runner.main(['--discussion-id', 'combined', '--output-dir', str(tmp_path)]) == 0
    path = tmp_path / 'combined.json'
    saved = load_discussion(path)
    assert len(saved.messages) == 24
    assert all(m.sentiment_score is not None and m.sentiment_label for m in saved.messages)
    assert saved.config.metadata['retrieval'] == 'week1_pgvector_k6'
    # Analytics defaults must never initialize either optional model engine.
    monkeypatch.setattr('src.analytics.stance.get_embedding_model', MagicMock(side_effect=AssertionError('unexpected model')))
    output = run_analytics_pipeline(path, output_path=tmp_path / 'analytics.json')
    assert output['metadata']['scored_snapshots'] == 24
    assert output['metadata']['input_status'] == 'completed'
    assert output['task1_opinion_trajectories']['metadata']['method'] == 'self_report_rules'
    assert output['task3_agent_influence']['top_influencer'] is None
    assert json.loads((tmp_path / 'analytics.json').read_text()) == output
    # Old saved discussions without sentiment fields still load.
    legacy = json.loads(path.read_text())
    for msg in legacy['messages']:
        msg.pop('sentiment_score'); msg.pop('sentiment_label')
    path.write_text(json.dumps(legacy))
    assert all(m.sentiment_score is None for m in load_discussion(path).messages)
    with pytest.raises(ValueError, match='overwrite'):
        run_analytics_pipeline(path, output_path=path)


@pytest.mark.parametrize('text,expected', [('I agree.', .8), ('I do not agree.', -.8), ("I don't agree.", -.8), ('I strongly disagree.', -.8), ('I do not oppose.', .8), ('The block was not effective.', None), ('The victory was a robbery.', None)])
def test_negation_and_unclassified_stances(text, expected):
    assert extract_numeric_stance({'stance': text}, prev_stance=.8) == expected


def test_changed_flag_cannot_freeze_numeric_opinion():
    assert extract_numeric_stance({'stance': 'I disagree.', 'changed_from_previous': False}, prev_stance=.8) == -.8


def test_missing_round_does_not_create_a_round_delta():
    result = compute_opinion_trajectories({'config': {'agent_ids': ['a']}, 'opinions': [
        {'agent_id': 'a', 'round_num': 0, 'stance': 'I agree.'},
        {'agent_id': 'a', 'round_num': 2, 'stance': 'I disagree.'},
    ]})
    assert result.trajectories['a'][1].opinion_change is None


def test_model_scoring_requires_explicit_poles():
    with pytest.raises(ValueError, match='pole'):
        score_snapshot_with_embeddings({'stance': 'Opinion'}, topic='Japan vs Spain')


def test_semantic_projection_uses_explicit_poles_without_amplification():
    model = MagicMock()
    model.encode.return_value = [[1, 0], [1, 0], [0, 1]]
    value = score_snapshot_with_embeddings({'stance': 'Opinion'}, model=model,
                                          positive_pole='The block worked', negative_pole='The block failed')
    assert value == .5
    assert model.encode.call_args.args[0][1:] == ['The block worked', 'The block failed']


@pytest.mark.parametrize('payload', [[], {}, [{'agent_id': 'unknown', 'round_num': 0, 'stance_value': .2}],
    [{'agent_id': 'a', 'round_num': 0, 'stance_value': float('nan')}],
    [{'agent_id': 'a', 'round_num': 0, 'stance_value': 5}],
    [{'agent_id': 'a', 'round_num': 0, 'stance_value': True}]])
def test_invalid_llm_scores_are_not_silently_replaced(payload):
    llm = MagicMock()
    llm.generate.return_value = {'content': json.dumps(payload)}
    with pytest.raises(ValueError):
        score_snapshots_with_llm('topic', [{'agent_id': 'a', 'round_num': 0, 'stance': 'Opinion'}], llm,
                                 positive_pole='Supports topic', negative_pole='Opposes topic')


def test_api_key_does_not_enable_llm_analytics(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'present')
    args = parse_args(['--input', 'discussion.json'])
    assert not args.use_llm and not args.use_embeddings
    with pytest.raises(SystemExit):
        parse_args(['--input', 'discussion.json', '--use-llm'])


def test_no_data_is_not_perfect_agreement():
    assert compute_round_agreement(0, []).agreement_score is None
    assert compute_round_agreement(0, [.5]).agreement_score is None
    assert compute_discussion_agreement({'config': {}, 'opinions': []}).mean_discussion_agreement is None
    assert compute_round_agreement(0, [-1, -1, -1, 1, 1, 1]).agreement_score == .4


def trajectories():
    return OpinionTrajectoryResult(discussion_id='test', agent_ids=['a', 'b'], trajectories={
        'a': [AgentStancePoint(agent_id='a', round_num=0, stance_value=.2), AgentStancePoint(agent_id='a', round_num=1, stance_value=.2, opinion_change=0)],
        'b': [AgentStancePoint(agent_id='b', round_num=0, stance_value=0), AgentStancePoint(agent_id='b', round_num=1, stance_value=1, opinion_change=1)],
    })


def test_overshoot_increases_distance_and_is_negative():
    data = {'config': {'agent_ids': ['a', 'b']}, 'messages': [{'round_num': 0, 'sender_id': 'a', 'recipient_ids': ['b']}]}
    result = compute_agent_influence(data, trajectories())
    assert result.get_influence_score('a') == -.6
    assert result.get_influence_score('b') is None
    assert result.top_influencer is None


def test_missing_routes_do_not_invent_influence():
    result = compute_agent_influence({'config': {'agent_ids': ['a', 'b']}, 'messages': []}, trajectories())
    assert all(inf.status == 'insufficient_data' and inf.influence_score is None for inf in result.agent_influences.values())
    assert result.get_ranked_influencers() == []


def test_query_aliases_preserve_evidence_and_bound_web_requests(monkeypatch):
    from src.tools.web_search import WebSearchTool
    from src.tools.knowledge_search import KnowledgeSearchTool
    retrieval = MagicMock()
    retrieval.retrieve.return_value = [source()]
    results = KnowledgeSearchTool(retrieval).run(queries=['low block', None])
    retrieval.retrieve.assert_called_once_with(query='low block')
    assert results[0]['metadata']['doc_id'] == 'doc_demo'
    web = WebSearchTool()
    call = MagicMock(return_value='Title: Example\nURL: https://example.test\nContent: Evidence')
    monkeypatch.setattr(web, '_search_single_query', call)
    web.run(queries=['first', 'first', 'second', 'third', None])
    assert [c.args[0] for c in call.call_args_list] == ['first', 'second']
