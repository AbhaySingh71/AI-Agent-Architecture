const topicInput = document.getElementById("topic");
const runButton = document.getElementById("runButton");
const statusBox = document.getElementById("status");
const results = document.getElementById("results");
const timeline = document.getElementById("timeline");
const finalAnswer = document.getElementById("finalAnswer");
const finalDecision = document.getElementById("finalDecision");
const summaryBadge = document.getElementById("summaryBadge");

function escapeHtml(value = "") {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

function setStatus(message, isError = false) {
    statusBox.textContent = message;
    statusBox.classList.remove("hidden", "error");
    if (isError) statusBox.classList.add("error");
}

function getAgentMeta(agentName) {
    const map = {
        web_search: { title: "DuckDuckGo Search", icon: "🌐", role: "Information Retrieval" },
        writer: { title: "Writer Agent", icon: "✍️", role: "Initial Draft Creation" },
        fact_checker: { title: "Fact-Checker Jury Member", icon: "🔍", role: "Ground-Truth Verification" },
        clarity_evaluator: { title: "Pedagogy & Clarity Jury Member", icon: "💡", role: "Beginner Simplicity & Analogy" },
        structure_evaluator: { title: "Structural Jury Member", icon: "📐", role: "Focus, Length & Example Check" },
        consensus_judge: { title: "Chief Consensus Judge", icon: "⚖️", role: "Jury Synthesis & Verdict" },
        reviser: { title: "Reviser Agent", icon: "🛠️", role: "Draft Correction & Polishing" }
    };
    return map[agentName] || { title: agentName, icon: "🤖", role: "Agent Node" };
}

function renderEvent(event, index) {
    const meta = getAgentMeta(event.agent);
    const revisionText = event.revision_count > 0 ? `Revision ${event.revision_count}` : "Step " + (index + 1);

    let body = "";
    let badgeHtml = "";

    if (event.agent === "web_search") {
        body = `<div class="search-box"><strong>Retrieved Web Search Context:</strong><br>${escapeHtml(event.search_context)}</div>`;
    } else if (event.agent === "writer" || event.agent === "reviser") {
        body = `<div class="answer">${escapeHtml(event.draft)}</div>`;
    } else if (event.agent === "fact_checker") {
        const review = event.fact_review || {};
        badgeHtml = review.decision ? `<span class="decision ${review.decision.toLowerCase()}">${escapeHtml(review.decision)}</span>` : "";
        body = `<div class="feedback"><strong>Fact Checker Verdict:</strong> ${escapeHtml(review.feedback || "Factual check passed cleanly.")}</div>`;
    } else if (event.agent === "clarity_evaluator") {
        const review = event.clarity_review || {};
        badgeHtml = review.decision ? `<span class="decision ${review.decision.toLowerCase()}">${escapeHtml(review.decision)}</span>` : "";
        body = `<div class="feedback"><strong>Clarity & Pedagogy Verdict:</strong> ${escapeHtml(review.feedback || "Explanation simplicity passed cleanly.")}</div>`;
    } else if (event.agent === "structure_evaluator") {
        const review = event.structure_review || {};
        badgeHtml = review.decision ? `<span class="decision ${review.decision.toLowerCase()}">${escapeHtml(review.decision)}</span>` : "";
        body = `<div class="feedback"><strong>Structure Verdict:</strong> ${escapeHtml(review.feedback || "Structural requirements passed cleanly.")}</div>`;
    } else if (event.agent === "consensus_judge") {
        const decision = event.consensus_decision || "PASS";
        badgeHtml = `<span class="decision ${decision.toLowerCase()}">Verdict: ${escapeHtml(decision)}</span>`;
        body = `<div class="action-plan"><strong>Jury Action Plan:</strong><br>${escapeHtml(event.synthesized_feedback || "All evaluators satisfied. Final answer approved.")}</div>`;
    }

    return `
        <article class="event node-${event.agent}">
            <div class="event-dot">${meta.icon}</div>
            <div class="event-card">
                <div class="event-top">
                    <div>
                        <div class="event-name">${escapeHtml(meta.title)}</div>
                        <div class="event-meta">${escapeHtml(meta.role)} · ${revisionText}</div>
                    </div>
                    ${badgeHtml}
                </div>
                ${body}
            </div>
        </article>
    `;
}

async function runAgentLoop() {
    const topic = topicInput.value.trim();
    if (!topic) {
        setStatus("Please enter a topic first.", true);
        return;
    }

    runButton.disabled = true;
    runButton.textContent = "Jury is evaluating…";
    results.classList.add("hidden");
    setStatus("1. Querying DuckDuckGo → 2. Writing Draft → 3. Convening Jury Panel (3 Evaluators) → 4. Consensus Judge…");

    try {
        const response = await fetch("/api/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic }),
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Something went wrong.");

        timeline.innerHTML = data.events.map(renderEvent).join("");
        finalAnswer.textContent = data.final_answer;
        finalDecision.textContent = data.final_decision || "PASS";
        finalDecision.className = `decision ${(data.final_decision || "pass").toLowerCase()}`;
        summaryBadge.textContent = `${data.revision_count} revision${data.revision_count === 1 ? "" : "s"} · DuckDuckGo Grounded`;

        statusBox.classList.add("hidden");
        results.classList.remove("hidden");
        results.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
        setStatus(error.message, true);
    } finally {
        runButton.disabled = false;
        runButton.textContent = "Run Jury Loop";
    }
}

runButton.addEventListener("click", runAgentLoop);
topicInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") runAgentLoop();
});

