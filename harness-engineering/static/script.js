const messageInput = document.getElementById("message");
const sendButton = document.getElementById("sendButton");
const btnText = document.getElementById("btnText");
const btnSpinner = document.getElementById("btnSpinner");

const resultCard = document.getElementById("resultCard");
const answerBox = document.getElementById("answer");
const routeBadge = document.getElementById("routeBadge");

const statLatency = document.getElementById("statLatency");
const statRouteMode = document.getElementById("statRouteMode");
const statSafety = document.getElementById("statSafety");
const statScore = document.getElementById("statScore");
const traceTimeline = document.getElementById("traceTimeline");

// Node Elements for Real-Time Execution Flow Visualizer
const node1 = document.getElementById("node-1");
const node1Tag = document.getElementById("node-1-tag");

const node2 = document.getElementById("node-2");
const node2Sub = document.getElementById("node-2-sub");
const node2Tag = document.getElementById("node-2-tag");

const node3 = document.getElementById("node-3");
const node3Title = document.getElementById("node-3-title");
const node3Tag = document.getElementById("node-3-tag");

const node4 = document.getElementById("node-4");
const node4Tag = document.getElementById("node-4-tag");

const node5 = document.getElementById("node-5");
const node5Tag = document.getElementById("node-5-tag");

function resetNodeFlow() {
    [node1, node2, node3, node4, node5].forEach((node) => {
        if (node) node.className = "node-card";
    });
    if (node1Tag) node1Tag.textContent = "Ready";
    if (node2Sub) node2Sub.textContent = "Hybrid Classifier";
    if (node2Tag) node2Tag.textContent = "Ready";
    if (node3Title) node3Title.textContent = "Specialist Agent";
    if (node3Tag) node3Tag.textContent = "Ready";
    if (node4Tag) node4Tag.textContent = "Ready";
    if (node5Tag) node5Tag.textContent = "Ready";
}

// Clickable Preset Prompt Pill Links
document.querySelectorAll(".preset-pill").forEach((button) => {
    button.addEventListener("click", () => {
        messageInput.value = button.dataset.text;
        messageInput.focus();
    });
});

// Handle Enter key in text input
messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        sendButton.click();
    }
});

sendButton.addEventListener("click", async () => {
    const message = messageInput.value.trim();

    if (!message) {
        alert("Please enter a question or click a preset prompt link.");
        return;
    }

    // Set Loading & Active Node Flow UI State
    sendButton.disabled = true;
    btnText.textContent = "Running Harness...";
    btnSpinner.classList.remove("hidden");

    resetNodeFlow();
    node1.className = "node-card active";
    node1Tag.textContent = "Checking...";

    resultCard.classList.remove("hidden");
    answerBox.className = "answer-text";
    answerBox.textContent = "Executing multi-agent harness pipeline...";
    routeBadge.textContent = "RUNNING";
    routeBadge.className = "route-badge";

    statLatency.textContent = "-- ms";
    statRouteMode.textContent = "--";
    statSafety.textContent = "Checking...";
    statScore.textContent = "--";
    traceTimeline.innerHTML = "";

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message: message,
            }),
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.message || "Server returned an error.");
        }

        // Real-Time Visual Workflow Flow Animation
        if (data.blocked) {
            node1.className = "node-card blocked";
            node1Tag.textContent = "Blocked";

            node2Tag.textContent = "Skipped";
            node3Tag.textContent = "Skipped";
            node4Tag.textContent = "Skipped";
            node5Tag.textContent = "Skipped";

            statSafety.textContent = "BLOCKED";
            statSafety.style.color = "#dc2626";
            routeBadge.textContent = "BLOCKED";
            routeBadge.className = "route-badge blocked";
        } else {
            // Step 1: Guardrail Passed
            node1.className = "node-card success";
            node1Tag.textContent = "Passed";

            // Step 2: Router Selected
            node2.className = "node-card success";
            node2Sub.textContent = data.route_mode === "llm_fallback" ? "LLM Classifier" : "Deterministic Match";
            node2Tag.textContent = `Routed (${Math.round(data.route_confidence * 100)}%)`;

            // Step 3: Specialist Agent Selected
            node3.className = "node-card success";
            const agentName = data.route.charAt(0).toUpperCase() + data.route.slice(1) + " Agent";
            node3Title.textContent = agentName;
            node3Tag.textContent = "Drafted";

            // Step 4: Quality Reviewer
            node4.className = "node-card success";
            node4Tag.textContent = "Validated";

            // Step 5: Final Output
            node5.className = "node-card success";
            node5Tag.textContent = "Completed";

            statSafety.textContent = "PASSED";
            statSafety.style.color = "#16a34a";
            routeBadge.textContent = data.route;
            routeBadge.className = `route-badge ${data.route}`;
        }

        // Render Telemetry & Stats
        statLatency.textContent = `${data.total_latency_ms} ms`;
        
        if (data.route_mode === "llm_fallback") {
            statRouteMode.textContent = `LLM Router (${Math.round(data.route_confidence * 100)}%)`;
        } else {
            statRouteMode.textContent = `Deterministic (100%)`;
        }

        statScore.textContent = `${Math.round(data.quality_score * 100)} / 100`;
        answerBox.textContent = data.answer;

        // Render Step Audit Log Items
        if (data.trace && data.trace.length > 0) {
            data.trace.forEach((stepText) => {
                const item = document.createElement("div");
                item.className = "timeline-step";
                item.textContent = stepText;
                traceTimeline.appendChild(item);
            });
        }
    } catch (error) {
        answerBox.className = "answer-text error";
        answerBox.textContent = `Execution Error: ${error.message || "Failed to connect to backend server."}`;
        statSafety.textContent = "ERROR";
        statSafety.style.color = "#dc2626";
        node1.className = "node-card blocked";
        node1Tag.textContent = "Error";
    } finally {
        sendButton.disabled = false;
        btnText.textContent = "Run Harness Loop";
        btnSpinner.classList.add("hidden");
    }
});
