# Week 5 — Frontend, Deployment & Production

## From Multi-Agent Prototype to Deployable Product

### 1. Overview

This week is the final stage of the project.
You will transform the systems built during Weeks 1–4 into a single usable, deployable application.

Until now, the project has been developed as several connected components:

```text
Week 1 Knowledge / Retrieval
       │
       ▼
Week 2 Agents
       │
       ▼
Week 3 Multi-Agent Discussion
       │
       ▼
Week 4 Analytics & Intelligence
```

This week you will bring everything together:

```text
┌────────────────────┐
│      Frontend      │
│                    │
│  Topic Selection   │
│  Discussion View   │
│   Analytics View   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│    Backend API     │
│                    │
│     Retrieval      │
│    Discussion      │
│     Analytics      │
└─────────┬──────────┘
          │
    ┌─────┴──────────┬────────────────┐
    ▼                ▼                ▼
Week 1 RAG     Week 3 Engine    Week 4 Analytics
```

The final result should be an application that another person can run, interact with, and understand without needing to manually execute the individual components from previous weeks.

The Week 5 milestone is explicitly to produce a deployable, production-ready application with a working frontend, integrated backend APIs, containerization, deployment documentation, and a final demonstration.

---

### 2. Why This Matters

A collection of working Python modules is not yet a usable product.
The final application should make the project's capabilities accessible through a single interface.

A reviewer should be able to:
* Open the application.
* Select a topic/domain.
* Start or load a discussion.
* Observe agents interacting.
* Inspect the discussion rounds.
* View opinion evolution.
* View agreement.
* View influence.
* View sentiment.
* Inspect the interaction graph.
* Run the application locally or access the deployed version.

This week is therefore about integration and productization, not about creating another isolated feature.

---

### 3. The Problem

Build a deployable web application that integrates the outputs of Weeks 1–4 behind a unified interface.

The application must provide:
* A frontend.
* A backend API layer.
* Integration with the Week 1 retrieval system.
* Integration with the Week 3 discussion engine.
* Integration with the Week 4 analytics engine.
* A discussion display.
* An analytics dashboard.
* Containerization.
* Deployment.
* Basic logging.
* A health-check endpoint.
* Production documentation.
* A final end-to-end demonstration.

---

### 4. Technology Choice

You may choose between the following frontend approaches:

**Option A — Streamlit**
```text
Streamlit
    │
    ▼
Backend / Python modules
```

**Option B — React + FastAPI**
```text
React
  │
  ▼
FastAPI
  │
  ▼
Backend modules
```

The Week 5 plan explicitly allows either Streamlit or React backed by FastAPI.

Choose the approach that best fits:
* Your experience.
* Your available time.
* The complexity of your existing backend.
* The final application's requirements.

You do not need to use the most sophisticated stack.
A smaller, reliable application is preferable to an ambitious application that does not work.

---

### 5. What You Need to Build

Your implementation must provide the following capabilities:
1. Web interface
2. Unified backend API
3. Week 1 integration
4. Week 3 integration
5. Week 4 integration
6. Discussion display
7. Analytics display
8. Docker containerization
9. Deployment
10. Logging
11. Health check
12. Production documentation
13. Final demonstration

---

### 6. Application Architecture

You are free to design the internal architecture.
A conceptual architecture might look like:

```text
       USER
         │
         ▼
┌──────────────────┐
│     Frontend     │
│                  │
│  Topic Selection │
│   Discussions    │
│    Analytics     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Backend API    │
│                  │
│     /topics      │
│   /discussions   │
│    /analytics    │
│     /health      │
└────────┬─────────┘
         │
 ┌───────┴───────┼────────────────┐
 ▼               ▼                ▼
Week 1 RAG  Week 3 Engine   Week 4 Engine
 │               │                │
 └───────────────┼────────────────┘
                 ▼
           Data / Storage
```

This is a conceptual design only.
Do not feel required to reproduce it exactly.

---

### 7. Frontend

#### Objective
Build the interface that users and reviewers will actually interact with.

The frontend must provide at least two major views:
* **Discussion**: Display the multi-agent conversation.
* **Analytics**: Display the results produced by Week 4.

The Week 5 plan requires both views to work with sample/mock data initially and then be connected to the real backend.

---

### 8. Frontend Requirements

The application should allow a user to:
* Select or enter a topic.
* Start or select a discussion.
* See participating agents.
* See the discussion rounds.
* Identify which agent produced each message.
* View the discussion history.
* Access the analytics for the discussion.

The exact UI design is up to you.
Do not spend the entire week trying to build a visually elaborate interface.

Prioritize:
$$\text{Functional} \;\longrightarrow\; \text{Clear} \;\longrightarrow\; \text{Reliable} \;\longrightarrow\; \text{Polished}$$

---

### 9. Topic Selection

The final demonstration must begin with topic/domain selection.
The user should have a clear mechanism for selecting or entering the subject of the discussion.

For example:
```text
┌─────────────────────────────────┐
│     Select Discussion Topic     │
│                                 │
│ [_____________________________] │
│                                 │
│       [Start Discussion]        │
└─────────────────────────────────┘
```

This is only an example.
Your implementation may use:
* A text input.
* A dropdown.
* A list of predefined topics.
* A combination.
* Another appropriate interface.

The final demo must demonstrate topic selection as part of the complete pipeline.

---

### 10. Discussion View

The discussion interface should display the conversation produced by Week 3.
At minimum, a reviewer should be able to identify:
* Agent.
* Round.
* Message.
* Discussion sequence.

For example:
```text
Round 1
  Agent A: "I believe ..."
  Agent B: "I disagree because ..."
  Agent C: "The evidence suggests ..."

Round 2
  Agent A: "After considering B's argument ..."
  ...
```

The exact visual design is your choice.

---

### 11. Discussion Requirements

The Week 5 acceptance test requires the UI to display at least three rounds of messages per agent for a sample run.

Therefore:
* At least 3 rounds are visible.
* Messages are associated with the correct agent.
* The discussion order can be understood.
* The user can distinguish different rounds.

---

### 12. Live Discussion vs Replay

The application may display discussions in either of two ways:
* **Live**: Messages appear as the discussion is happening.
* **Replay**: A completed discussion is loaded and displayed round by round.

The Week 5 specification allows either approach.
If implementing live interaction is difficult, a high-quality replay of a real Week 3 discussion is acceptable.
If you implement live updates, document how they work.

---

### 13. Analytics Dashboard

The frontend must expose the Week 4 analytics.
At minimum, the interface must surface:
* Opinion trajectory.
* Agreement.
* Influence.
* Sentiment.
* Interaction graph.

The Week 5 plan specifically identifies these Week 4 outputs as the analytics displayed by the dashboard.

---

### 14. Opinion Trajectory

Display the Week 4 opinion trajectory visualization.
The user should be able to see how agent stances changed over discussion rounds.

For example:
```text
Stance
  1 │    A────────
    │   /
  0 │  B───
    │
 -1 │
    └────────────────
       R1   R2   R3
```

Use the actual visualization generated by Week 4 or expose the same information through a frontend visualization.
The exact implementation is up to you.

---

### 15. Agreement

Display the agreement/disagreement results generated by Week 4.
The user should be able to understand how group alignment changed across rounds.

Possible presentation methods include:
* Line chart.
* Metric cards.
* Table.
* Combination.

For example:
```text
Agreement
Round 1  ███████░░░  0.70
Round 2  █████████░  0.88
Round 3  ██████░░░░  0.61
```

This is only illustrative.

---

### 16. Influence

Display the per-agent influence results from Week 4.

For example:
```text
Influence
Agent A  0.81
Agent B  0.52
Agent C  0.31
Agent D  0.18
```

Possible visualizations include:
* Bar chart.
* Ranked list.
* Metric cards.
* Network visualization.

The exact presentation is your choice.

---

### 17. Sentiment

Expose the sentiment analysis produced by Week 4.

Possible views include:
* Sentiment per message.
* Sentiment by agent.
* Sentiment by round.
* Overall sentiment distribution.

You do not need to expose every possible aggregation.
Choose a representation that makes the information useful and understandable.

---

### 18. Interaction Graph

Display the Week 4 interaction graph.
The graph should show:
* Agents.
* Relationships.
* Interaction strength.

The Week 4 implementation already generates the interaction graph, so the Week 5 application should integrate that output rather than independently recreating the graph logic unless there is a good reason to do so.

---

### 19. Backend API

The backend is the integration layer connecting the frontend to Weeks 1, 3, and 4.
The Week 5 plan expects the previous modules to be wrapped behind unified backend endpoints, with FastAPI given as the example implementation.

The exact API design is up to you.
However, the frontend should not need to understand the internal implementation of:
* Retrieval.
* Agent orchestration.
* Discussion persistence.
* Analytics computation.

---

### 20. API Responsibilities

Your backend should provide endpoints capable of supporting at least:
* Topic / domain selection
* Discussion creation or retrieval
* Discussion history
* Analytics
* Health check

You may expose additional endpoints if useful.

---

### 21. Suggested API

The following is an example rather than a required API:
```http
GET /health
GET /topics
POST /discussions
GET /discussions/{discussion_id}
GET /discussions/{discussion_id}/analytics
```

You may choose different routes.
The important thing is that the API cleanly exposes the functionality required by the frontend.

---

### 22. API Contracts

Document the request and response format for every public endpoint.

For example:
```http
GET /discussions/{discussion_id}
```
Response:
```json
{
  "discussion_id": "...",
  "topic": "...",
  "agents": [...],
  "rounds": [...]
}
```

And:
```http
GET /discussions/{discussion_id}/analytics
```
Response:
```json
{
  "opinion_change": {...},
  "agreement": {...},
  "influence": {...},
  "sentiment": {...}
}
```

These are examples only.
Your actual schemas should match your implementation.

---

### 23. API Acceptance Criteria

A reviewer should be able to:
* Start or retrieve a discussion.
* Retrieve discussion history.
* Retrieve analytics for a discussion.
* Receive valid structured responses.
* Detect API failures clearly.

The Week 5 acceptance test requires each unified backend route to return a valid response for a sample discussion run ID.

---

### 24. Integration With Week 1

The final application must integrate the Week 1 retrieval infrastructure.
The exact way this appears in the UI is your choice.

The integration may occur when:
* A discussion is created.
* Agents retrieve information.
* A user searches the knowledge base.
* Another part of the application requires retrieval.

The important point is that the final application should use the actual Week 1 system rather than replacing it with mock data.

---

### 25. Integration With Week 3

The application must integrate the Week 3 discussion engine.
The final application should be able to access a real discussion run and display its results.

The Week 3 discussion engine provides the data necessary for:
* Agents
* Rounds
* Messages
* Graph
* Opinions
* Retrieved context

The final application should consume those outputs through the integration layer.

---

### 26. Integration With Week 4

The application must integrate the Week 4 analytics engine.
The frontend should not independently reimplement:
* Opinion change calculations.
* Agreement calculations.
* Influence calculations.
* Sentiment calculations.

Instead:
```text
Frontend
   │
   ▼
Backend
   │
   ▼
Week 4 Analytics Engine
   │
   ▼
Analytics Result
```

This keeps the analytics logic centralized.

---

### 27. Mock Data During Development

You may initially use mock data while building the frontend.
This is encouraged because it allows you to develop the UI independently of the backend.
However, mock data must eventually be replaced with real API responses.

The Week 5 plan explicitly separates the initial UI work with sample/mock data from the later integration step.
Final acceptance should use real outputs from the previous weeks.

---

### 28. Error Handling

The application should handle common failures gracefully.
Consider:
* Backend unavailable
* Discussion not found
* Analytics unavailable
* Retrieval failure
* Invalid topic
* Malformed API response
* LLM/API failure
* Database failure

The user should receive a meaningful error rather than a blank page or unexplained exception.

---

### 29. Loading States

Long-running operations should provide some indication that work is happening.
For example:
* Starting discussion...
* Agent A is thinking...
* Round 2...
* Generating analytics...

The exact implementation depends on your frontend architecture.
The goal is to prevent the application from appearing frozen during long-running operations.

---

### 30. Docker Containerization

The entire application must be containerized.
The Week 5 plan requires Docker packaging so that the application can run consistently across environments.

At minimum, provide:
* `Dockerfile`

You may additionally use:
* `docker-compose.yml`

if your architecture contains multiple services.

---

### 31. Container Requirements

The Docker setup must:
* Install required dependencies.
* Configure the application.
* Start the necessary services.
* Expose the required ports.
* Allow the application to be accessed from outside the container.

The exact image, base image, process manager, and service architecture are your choices.

---

### 32. Docker Acceptance Test

A reviewer must be able to build the application successfully.
For example:
```bash
docker build -t opinion-platform .
```
The build must complete without errors.
The Week 5 acceptance criterion explicitly requires a successful docker build.

---

### 33. Containerized Run

After building the image, the application must be reachable.
For example:
```bash
docker run -p <port>:<port> opinion-platform
```
or:
```bash
docker compose up --build
```
The exact command depends on your architecture.
Document the actual command in this README / DEPLOYMENT.md.

---

### 34. Local Container Acceptance

The reviewer must be able to:
* Build the container.
* Start it.
* Open the documented port.
* Access the application.
* Run the basic demonstration.

The Week 5 acceptance test requires the UI to be reachable after `docker run` or `docker compose up`.

---

### 35. Deployment

Deploy the containerized application to the free cloud platform selected during the program kickoff.
The Week 5 source plan lists:
* Azure
* AWS
* Kaggle
* GitHub Codespaces

as possible platforms.
Use the platform selected by the program rather than independently choosing another service unless instructed otherwise.

---

### 36. Deployment Requirements

The deployed application must be reachable by the reviewer.
Provide either:
* Public URL
or:
* Access instructions

depending on the selected deployment environment.
The deployment must expose a functioning application rather than merely uploading source code or a Docker image.

---

### 37. Deployment Acceptance Test

The deployed instance must respond successfully to a health-check request.
For example:
```bash
curl https://your-deployment/health
```
The exact URL depends on the deployment.
The Week 5 acceptance criterion requires the deployed instance to respond to a health check.

---

### 38. Health Check

Implement a basic health endpoint.
For example:
```http
GET /health
```
A successful response could look like:
```json
{
  "status": "ok"
}
```
This is only an example.
The endpoint should return an appropriate HTTP success response when the application is functioning.

---

### 39. Health Check Requirements

The health endpoint should:
* Be lightweight.
* Not require a full discussion run.
* Return quickly.
* Clearly indicate application status.

The Week 5 acceptance test requires:
```http
GET /health
```
to return HTTP 200 with a status payload.

---

### 40. Logging

Add basic application logging.
At minimum, log important events such as:
* Application startup
* API requests
* Errors
* Discussion creation
* Discussion retrieval
* Analytics requests
* Health checks

You do not need to build a sophisticated observability platform.
The objective is to make it possible to understand what the application is doing and diagnose basic failures.

---

### 41. Structured Logging

Where practical, logs should contain:
* Timestamp
* Log level
* Event/message
* Relevant identifier

For example:
```text
2026-08-08 10:15:32 INFO discussion_created id=abc123
2026-08-08 10:16:03 INFO analytics_requested id=abc123
2026-08-08 10:16:07 ERROR analytics_failed id=abc123
```
The exact format is up to you.
The Week 5 plan requires timestamps and key events such as requests and errors.

---

### 42. Logging Acceptance Test

A reviewer should be able to:
* Start the application.
* Make a sample request.
* Inspect the logs.
* Find a corresponding log entry.

The Week 5 acceptance criterion specifically requires log output showing an entry for a sample request.

---

### 43. Production Configuration

Separate configuration from source code.
Configuration may include:
* API keys
* Database URL
* LLM configuration
* Model names
* Service URLs
* Ports
* Environment

Provide:
* `.env.example`

where appropriate.
Never commit secrets.

---

### 44. Environment Variables

Document every required environment variable.
For example:
```env
VARIABLE_NAME=
ANOTHER_VARIABLE=
DATABASE_URL=
```
Do not include actual secrets.
Explain:
* What the variable controls.
* Whether it is required.
* Example values where safe.

---

### 45. Production Documentation

Create a:
* `DEPLOYMENT.md`

or an equivalent deployment section in the README.
The documentation must cover:
* Local setup.
* Environment variables.
* Docker build.
* Docker run.
* Deployment.
* Troubleshooting.

The source plan explicitly requires documentation that allows someone unfamiliar with the project to operate it.

---

### 46. Troubleshooting

Include common problems and solutions.
For example:
```text
Problem: Frontend cannot connect to backend.
Possible cause: Incorrect API URL.
Solution: Check BACKEND_URL.
```

Other useful categories include:
* Docker issues.
* Environment variables.
* Port conflicts.
* API connectivity.
* Missing dependencies.
* Deployment failures.
* External service/API failures.

---

### 47. Suggested Repository Structure

Keep the structure simple.
One possible starting point:
```text
.
├── README.md
├── DEPLOYMENT.md
├── .gitignore
├── .env.example
├── Dockerfile
├── docker-compose.yml
│
├── frontend/
│   └── ...
│
├── backend/
│   └── ...
│
├── src/
│   └── ...
│
├── tests/
│   └── ...
│
└── reports/
    └── ...
```

This is only a suggestion.
If you use Streamlit, React, FastAPI, or another architecture, organize the repository accordingly.
Do not create directories simply because they appear in this example.

---

### 48. Testing Requirements

Your repository should include tests or reproducible checks for the critical application behavior.
At minimum, verify:

#### Frontend
* Frontend starts.
* Main views render.
* Discussion view works.
* Analytics view works.

#### Backend
* API starts.
* Required routes respond.
* Sample discussion can be retrieved.
* Analytics can be retrieved.

#### Integration
* Frontend receives real backend data.
* Discussion data is displayed.
* Analytics data is displayed.

#### Docker
* Image builds successfully.
* Container starts.
* Application is reachable.

#### Health
* `/health` returns HTTP 200.

#### Deployment
* Deployed application is reachable.
* Deployed `/health` responds successfully.

---

### 49. Acceptance Criteria

The project is considered complete when all of the following are satisfied.

#### Frontend
* Frontend runs locally.
* Placeholder page was successfully replaced by the actual application.
* Discussion view exists.
* Analytics view exists.
* Topic/domain selection exists.
* UI works with real backend data.
*(The Week 5 source plan requires the frontend to render locally and provide discussion and analytics views.)*

#### Backend
* Unified backend API exists.
* Week 1 retrieval is integrated.
* Week 3 discussion engine is integrated.
* Week 4 analytics engine is integrated.
* API routes return valid responses for a sample discussion.
* Frontend uses real API responses.
*(These are the required integration goals in the Week 5 plan.)*

#### Discussion
* A real discussion can be loaded or started.
* At least 3 rounds can be displayed.
* Messages are associated with agents.
* Discussion order/rounds are clear.
* The discussion is not merely mock data in the final demonstration.

#### Analytics
* Opinion trajectory is displayed.
* Agreement is displayed.
* Influence is displayed.
* Sentiment is displayed.
* Interaction graph is displayed.
* Analytics come from Week 4.
*(The source acceptance test specifically requires the UI to display the Week 4 opinion trajectory and interaction graph.)*

#### Docker
* `Dockerfile` exists.
* `docker build` succeeds.
* Container starts successfully.
* UI is reachable from the documented port.

#### Deployment
* Application is deployed.
* Deployment is reachable.
* Health check works on deployment.
* Deployment instructions are documented.

#### Monitoring
* Application logs exist.
* Requests are logged.
* Errors are logged.
* `/health` exists.
* `/health` returns HTTP 200 when healthy.

#### Documentation
* `README` contains setup instructions.
* Dependencies are documented.
* Environment variables are documented.
* Docker instructions exist.
* Deployment instructions exist.
* Troubleshooting exists.
* Reviewer reproduction steps are exact.

#### Final Demonstration
* Topic/domain selection is demonstrated.
* Discussion is demonstrated.
* At least three rounds are shown.
* Analytics dashboard is demonstrated.
* Application is demonstrated in its deployed form.

---

### 50. Expected Deliverables

At the end of the week, your repository should contain:
1. **Working frontend**: The main user-facing application.
2. **Unified backend API**: The integration layer for the previous weeks.
3. **Discussion interface**: A view showing the multi-agent discussion.
4. **Analytics dashboard**: A view showing the Week 4 results.
5. **Docker configuration**: A reproducible containerized application.
6. **Deployment**: A reachable deployed instance.
7. **Logging**: Basic application logging.
8. **Health check**: A working `/health` endpoint.
9. **Production documentation**: Setup, deployment, configuration, and troubleshooting documentation.
10. **Final demonstration**: A short presentation or recorded/live walkthrough of the complete system.

---

### 51. Reviewer Reproduction

This section is particularly important.
A reviewer unfamiliar with your implementation should be able to reproduce the application using the instructions in your repository.

Your README must provide exact commands for:
* Local development
* Running the backend
* Running the frontend
* Running tests
* Building Docker
* Running Docker
* Deployment
* Health check

Replace every placeholder with the actual commands for your implementation.

---

### 52. Docker Compose

If your implementation contains multiple services, you may use:
`docker-compose.yml`

For example:
```text
┌──────────────────┐
│     Frontend     │
│                  │
│      :3000       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│     Backend      │
│                  │
│      :8000       │
└────────┬─────────┘
         │
         ▼
  Other services
```

This is optional.
A single-container architecture is perfectly acceptable if it meets the requirements.

---

### 53. Security

Do not commit:
* API keys.
* Access tokens.
* Passwords.
* Private credentials.
* Production secrets.

Use environment variables or another appropriate secret-management mechanism.
Also avoid exposing unnecessary internal services publicly.
This does not need to become a full security engineering project.
Apply reasonable practices appropriate for a student production deployment.

---

### 54. Performance

You do not need to optimize the system for massive traffic.
However, consider:
* Long LLM requests.
* Large discussion histories.
* Large analytics responses.
* Repeated analytics computation.
* Frontend loading time.

Avoid unnecessarily recomputing expensive operations.
For example, if Week 4 analytics have already been generated for a discussion, the frontend should ideally retrieve the existing results rather than recalculating them every time the user opens the dashboard.

---

### 55. User Experience

The application should make it obvious:
* Where am I?
* What discussion am I viewing?
* Which agents are participating?
* What round is being displayed?
* What do the analytics mean?
* Is the application currently processing something?
* Did something fail?

A simple interface with clear information is preferable to a visually complex interface that is difficult to understand.

---

### 56. Final Demo Scenario

Your final demonstration should use one complete scenario.

For example:
```text
 1. Open deployed application
         │
         ▼
 2. Select a topic
         │
         ▼
 3. Start discussion
         │
         ▼
 4. Agents interact
         │
         ▼
 5. Display Round 1
         │
         ▼
 6. Display Round 2
         │
         ▼
 7. Display Round 3
         │
         ▼
 8. Open analytics
         ├── Opinion trajectory
         ├── Agreement
         ├── Influence
         ├── Sentiment
         └── Interaction graph
         │
         ▼
 9. Explain key findings
```

This should demonstrate that the project functions as one system rather than five independent weekly submissions.

---

### 57. Final Presentation

Prepare a short final presentation or recorded/live walkthrough.
The final demonstration should cover:
1. **Problem**: What is the platform trying to accomplish?
2. **Architecture**: How do Weeks 1–5 connect?
3. **Topic selection**: Show the user selecting a topic/domain.
4. **Discussion**: Show the agents interacting.
5. **Analytics**: Show the resulting analytics.
6. **Deployment**: Show the deployed application.
7. **Key findings**: Briefly explain what the simulation revealed.

The Week 5 plan explicitly defines this final demonstration as the capstone proof that the five-week project works end-to-end.

---

### 58. End-to-End Architecture

Your final system should conceptually demonstrate:

```text
       USER
         │
         ▼
┌───────────────┐
│   Frontend    │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Backend API  │
└───────┬───────┘
        │
  ┌─────┴─────────┼────────────────┐
  │               │                │
  ▼               ▼                ▼
┌─────────┐ ┌────────────┐ ┌────────────┐
│ Week 1  │ │   Week 3   │ │   Week 4   │
│   RAG   │ │ Discussion │ │ Analytics  │
└─────────┘ └────────────┘ └────────────┘
                  │              │
                  ▼              ▼
              Discussion     Analytics
               History        Results
                  │              │
                  └───────┬──────┘
                          ▼
                     Frontend UI
```

This is the architecture you are trying to make actually work, not necessarily the exact architecture you must implement.

---

### 59. Engineering Decisions

You should document the major decisions made during this week.
At minimum explain:
* **Frontend**: Why did you choose Streamlit or React?
* **Backend**: Why did you choose your API architecture?
* **API design**: How are the previous weeks exposed?
* **Deployment**: Why was the selected deployment architecture used?
* **Docker**: Why did you choose one or multiple containers?
* **Data flow**: How does a discussion move from creation to analytics to display?
* **Tradeoffs**: What did you intentionally choose not to implement because of time or complexity?

---

### 60. What Not to Do

Do not spend the majority of the week on cosmetic UI features while the underlying application is broken.

Avoid prioritizing:
* Fancy animations
* Complex authentication
* Unnecessary microservices
* Complicated cloud infrastructure
* Custom design systems

over:
* Working integration
* Reliable API
* Working discussion
* Working analytics
* Docker
* Deployment
* Documentation

The objective is a functioning final product.

---

### 61. Learning Resources

The following resources support the frontend, backend integration, containerization, and deployment tasks in this week. Required resources should be studied as part of the week's work; optional resources provide additional support for Fellows who want more practice with FastAPI.

#### Required Resources

* **End-to-End ML Deployment (FastAPI, Streamlit, Docker)**
  * Study time: ~45 minutes
  * [https://www.youtube.com/watch?v=YBn9zpyhMgU](https://www.youtube.com/watch?v=YBn9zpyhMgU)
  * Relevant to: Developing the web interface; Integrating backend APIs; Containerizing the application.
  * *This resource directly covers the full stack required this week: FastAPI backend, Streamlit frontend, and Docker containerization.*

* **Complete FastAPI Tutorial — Arabic Video**
  * Study time: ~60 minutes
  * [https://www.youtube.com/watch?v=yvyKtJVVIdk](https://www.youtube.com/watch?v=yvyKtJVVIdk)
  * Relevant to: Integrating backend APIs; Building the unified FastAPI backend; Structuring API endpoints.
  * *This is a comprehensive FastAPI walkthrough directly supporting the backend API integration task.*

* **Streamlit Dashboards and Data Apps — Arabic Video**
  * Study time: ~40 minutes
  * [https://www.youtube.com/watch?v=o5Wt0QS7Oco](https://www.youtube.com/watch?v=o5Wt0QS7Oco)
  * Relevant to: Developing the web interface; Displaying live discussions; Displaying analytics.
  * *This resource is directly relevant if you choose Streamlit for the frontend.*

* **Docker from Scratch to Mastery — Arabic Video**
  * Study time: ~50 minutes
  * [https://www.youtube.com/watch?v=9yoe8dBvAZ0](https://www.youtube.com/watch?v=9yoe8dBvAZ0)
  * Relevant to: Containerizing the application; Writing Dockerfiles; Running the application in containers.
  * *This provides a full Docker walkthrough supporting the containerization subtask.*

* **FastAPI Code Repository**
  * Study time: ~20 minutes
  * [https://github.com/Pythonation/FastAPI_Tutorial](https://github.com/Pythonation/FastAPI_Tutorial)
  * Relevant to: Integrating backend APIs; Structuring the FastAPI backend; Using a reference implementation while building the API layer.
  * *The source specifically identifies this as a reference repository that can be used as a starting template.*

#### Optional Resources

* **FastAPI Python Web Fundamentals — Arabic Course**
  * Study time: ~90 minutes
  * [https://www.m3aarf.com/certificate/27276/](https://www.m3aarf.com/certificate/27276/)
  * Relevant to: Learning FastAPI fundamentals; Integrating backend APIs.
  * *This is a broader FastAPI fundamentals course and is particularly useful if you are new to the framework.*

* **Build First API with FastAPI — Arabic Video**
  * Study time: ~25 minutes
  * [https://www.youtube.com/watch?v=NcPQm2KkIWE](https://www.youtube.com/watch?v=NcPQm2KkIWE)
  * Relevant to: Integrating backend APIs; Learning the basics of FastAPI endpoint development.
  * *This is a beginner-level supplementary resource if you want a gentler introduction before going through the complete tutorial.*

* **FastAPI Routing and Schemas — Arabic Video**
  * Study time: ~25 minutes
  * [https://www.youtube.com/watch?v=TXkh6XICWm8](https://www.youtube.com/watch?v=TXkh6XICWm8)
  * Relevant to: Integrating backend APIs; Designing routes and schemas; Structuring endpoints.
  * *This is useful if you need more focused guidance on FastAPI routing and schema design.*

#### Resource-to-Task Mapping

| Resource | Relevant Task(s) | Required? |
| :--- | :--- | :--- |
| End-to-End ML Deployment (FastAPI, Streamlit, Docker) | Develop web interface; Integrate backend APIs; Containerize | Yes |
| Complete FastAPI Tutorial | Integrate backend APIs | Yes |
| Streamlit Dashboards and Data Apps | Develop web interface; Display discussions & analytics | Yes |
| Docker from Scratch to Mastery | Containerize application | Yes |
| FastAPI Code Repository | Integrate backend APIs | Yes |
| FastAPI Python Web Fundamentals | Integrate backend APIs | Optional |
| Build First API with FastAPI | Integrate backend APIs | Optional |
| FastAPI Routing and Schemas | Integrate backend APIs | Optional |

---

### 62. Definition of Done

You are done when you can demonstrate the following:

```text
       USER
         │
         ▼
┌─────────────────┐
│ Select a Topic  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Start Discussion │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Multi-Agent   │
│   Discussion    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
 Round 1   Round 2 ...
    │
    ▼
 Round 3
    │
    ▼
┌───────────────────┐
│ Analytics Engine  │
└─────────┬─────────┘
          │
  ┌───────┼───────┐
  ▼       ▼       ▼
Opinion Agreement Influence
  │
  └───────┬───────┘
          ▼
      Sentiment
          │
          ▼
  Interaction Graph
          │
          ▼
      Dashboard
          │
          ▼
     Docker Image
          │
          ▼
      Deployment
          │
          ▼
  Public / Hosted App
```

At minimum, the final application must demonstrate:
* A working frontend.
* Topic/domain selection.
* A real multi-agent discussion.
* At least three rounds displayed.
* Integrated Week 1 retrieval infrastructure.
* Integrated Week 3 discussion engine.
* Integrated Week 4 analytics.
* Opinion trajectory.
* Agreement.
* Influence.
* Sentiment.
* Interaction graph.
* Working backend APIs.
* Docker build.
* Containerized application.
* Deployed application.
* `/health` endpoint.
* Application logging.
* Deployment documentation.
* Final end-to-end demonstration.

The final goal is simple:
> Someone who did not build Weeks 1–4 should be able to open the application, run a discussion, understand what happened, and inspect the resulting analytics without touching the underlying implementation.

That is the final product.
