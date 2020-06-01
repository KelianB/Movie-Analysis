const TYPE_SPEECH = "SPEECH";
const TYPE_CHARACTER = "CHARACTER";
const TYPE_LOCATION = "LOCATION";
const TYPE_DIRECTION = "DIRECTION";

// Get DOM elements for later use
let dom = {};
dom.breakdownSelect = $("#content-character-breakdown select");
dom.breakdownMeta = $("#character-breakdown-meta");
dom.interactionGraphContainer = $("#interaction-graph-container");
dom.characterInteractionsMeta = $("#character-interactions-meta");
dom.characterInteractionsSelectA = $("#character-interactions-select-a");
dom.characterInteractionsSelectB = $("#character-interactions-select-b");    
dom.characterInteractionsCompute = $("#character-interactions-compute");
dom.characterInteractionsGraph = $("#character-interactions-graph");
dom.directionSentimentGraph = $("#direction-sentiment-graph");
dom.characterBreakdownGraph = $("#character-breakdown-graph");

// Store the sigma graph for character interactions
let interactionGraph = null;

// Listeners that are triggered whenever a section is shown
let sectionShowListeners = {
    "content-interaction-graph": () => {
        if(interactionGraph)
            interactionGraph.refresh();
    }
};

// Store the current movie globally
let movie = null;

// Register resize listeners
function onResize() {
    dom.interactionGraphContainer.width($("main").width());
    dom.interactionGraphContainer.height(window.innerHeight - $("#top-nav").height() - 100);
}
window.addEventListener("resize", onResize);
onResize();

// Create a FileReader to be used for reading the analyzed scripts in JSON format.
let fr = new FileReader();
fr.onload = () => {
    displayMovie(JSON.parse(fr.result));
    enableMovieSpecificSections();
};

function displayMovie(newMovie) {
    movie = newMovie;

    // Read settings
    let minLinesThreshold = $("#min-lines-threshold").val();
    minLinesThresholdGraph = $("#min-lines-threshold-graph").val();
    let settings = {
        minLinesThreshold: minLinesThreshold,
        minLinesThresholdGraph: minLinesThresholdGraph
    };

    // Sort characters by decreasing line count
    movie.sortedCharacterNames = Object.keys(movie.characters);
    movie.sortedCharacterNames.sort((a,b) => movie.characters[b].line_count - movie.characters[a].line_count);

    // Fill character <select>
    fillCharacterSelect(dom.breakdownSelect, movie, minLinesThreshold);
    fillCharacterSelect(dom.characterInteractionsSelectA, movie, minLinesThreshold);
    fillCharacterSelect(dom.characterInteractionsSelectB, movie, minLinesThreshold);
    dom.characterInteractionsSelectB.val(movie.sortedCharacterNames[1]);

    // Update character table
    let characterBreakdownBody = $("#character-table tbody");
    characterBreakdownBody.empty();

    let i = 1;
    for(let cname of movie.sortedCharacterNames) {
        let c = movie.characters[cname];
        if(c.line_count <= minLinesThreshold)
            continue;

        characterBreakdownBody.append($("<tr>").append(
            $("<td>").text(i++),
            $("<td>").text(c.name),
            $("<td>").text(c.line_count),
            $("<td>").text(Math.round(c.avg_cs*1000)/1000).css("background-color", getSentimentColor(c.avg_cs))
        ));
    }

    // Show direction sentiment
    createDirectionSentimentChart(movie, dom.directionSentimentGraph);

    // Create the character interaction graph
    let interactionGraph = createSocialGraph(movie, settings);

    // Redirect to graph display
    setTimeout(() => {
        $(".nav-link[data-div='content-interaction-graph']").click();

        interactionGraph.refresh();
        setTimeout(() => {
            interactionGraph.killForceAtlas2();
        }, 2500);
        interactionGraph.startForceAtlas2({
            scalingRatio: 5000,
            gravity: 0.01,
            slowDown: 50,
        });
    }, 100);
}

function createSocialGraph(movie, settings) {
    let g = {
        nodes: [],
        edges: []
    };

    for(let cname in movie.characters) {
        let c = movie.characters[cname];
        
        if(c.line_count <= settings.minLinesThresholdGraph)
            continue;

        g.nodes.push({
            id: c.name,
            label: c.name,
            x: Math.random() * dom.interactionGraphContainer.width(),
            y: Math.random() * dom.interactionGraphContainer.height(),
            size: Math.pow(c.line_count, 0.7),
            color: getSentimentColor(c.avg_cs),
        });
    }

    for(let ciName in movie.characters) {
        let ci = movie.characters[ciName];
        if(ci.line_count <= settings.minLinesThresholdGraph)
            continue;
        for(let cjName in movie.characters) {
            let cj = movie.characters[cjName];
            let co = movie.cooccurrences[ci.name][cj.name]; 
            if(ciName == cjName || co.count == 0 || cj.line_count <= settings.minLinesThresholdGraph)
                continue;
            g.edges.push({
                id: ci.name + "-" + cj.name,
                source: ci.name,
                target: cj.name,
                size: Math.pow(co.count, 1.2),
                color: getSentimentColor(co.avg_cs)
            });
        }
    }

    // Instantiate sigma:
    interactionGraph = new sigma({graph: g, renderers: [{type: "canvas", container: "interaction-graph-container"}]});
    interactionGraph.settings({
        maxEdgeSize: 10,
        maxNodeSize: 30,
        scalingMode: "inside",
        sideMargin: 100,
        enableEdgeHovering: true
    });

    // Register node click event
    interactionGraph.bind("clickNode", (e) => {
        // console.log(e.type, e.data.node.label, e.data.captor); 
        let name = e.data.node.label;
        $(".nav-link[data-div='content-character-breakdown']").click();
        dom.breakdownSelect.val(name).change();
    });
    interactionGraph.bind("clickEdge", (e) => {
        let edge = e.data.edge;
        $(".nav-link[data-div='content-character-interactions']").click();
        dom.characterInteractionsSelectA.val(edge.source);
        dom.characterInteractionsSelectB.val(edge.target);
        dom.characterInteractionsCompute.click();
    });
        
    return interactionGraph;
}

function showCharacterBreakdown(name) {
    let character = movie.characters[name];

    dom.breakdownMeta.empty();
    dom.breakdownMeta.append(
        $("<table>")
            .append($("<tr>")
                .append($("<td>").text("Number of lines:"))
                .append($("<td>").text(character["line_count"]))
            )
            .append($("<tr>")
                .append($("<td>").text("Average sentiment score:"))
                .append($("<td>").text(Math.round(character.avg_cs*1000)/1000).css("color", getSentimentColor(character.avg_cs)))
            )
    );
    
    // Attempt at average per scene
    let lineIndices = [], lines = [], lineIndex = 0;
    let scoresSceneAvg = [];
    let scores = [];
    let sceneLines = 0, sceneSum = 0;

    for(let i = 1; i < movie.entries.length; i++) {
        let prevE = movie.entries[i-1];
        let e = movie.entries[i];
        if(e.type == TYPE_SPEECH && prevE.type == TYPE_CHARACTER) {
            if(prevE.content == name) {
                lineIndices.push(lineIndex);
                lines.push(e.content);
                scores.push(e.cs);
                sceneLines++;
                sceneSum += e.cs;
            }
            lineIndex++;
        }
        else if(e.type == TYPE_LOCATION) {
            let sceneAvg = sceneSum / sceneLines;
            for(let j = 0; j < sceneLines; j++)
                scoresSceneAvg.push(sceneAvg);
            sceneLines = 0;
            sceneSum = 0;
        }
    }

    let canvas = $("<canvas>");
    let chartCtx = canvas[0].getContext("2d");
    dom.characterBreakdownGraph.empty().append(canvas);

    new Chart(chartCtx, {
        type: "line",
        data: {
            labels: lineIndices,
            datasets: [
                {data: scores, label: "Sentiment score (compound)", fill: false},
                {data: smoothMovingWindow(scores), label: "Sentiment score (compound), smoothed", fill: false, borderColor: "rgb(60,140,180)"}
            ]
        },
        options: {
            responsive: true,
            title: {
                display: true,
                text: "Evolution of character sentiment during the movie"
            },
            tooltips: {
                callbacks: {
                    title: (tooltipItem, data) => "",
                    label: (tooltipItem, data) => formatLabel(lines[tooltipItem.index])
                },
            }
        }
    });
}


function showCharacterInteractions(nameA, nameB) {
    let lineIndices = [], lines = [], lineIndex = 0;
    let scoresA = [], scoresB = [];
    let numInteractions = 0;

    for(let i = 2; i < movie.entries.length - 2; i++) {
        let e = movie.entries[i];
        if(e.type == TYPE_CHARACTER) {
            let speech = movie.entries[i+1];
            let isA = e.content == nameA, isB = e.content == nameB;
            
            let previousCharacter = getPreviousCharacter(movie, i), nextCharacter = getNextCharacter(movie, i);
            let aToB = isA && (previousCharacter == nameB || nextCharacter == nameB);
            let bToA = isB && (previousCharacter == nameA || nextCharacter == nameA);

            if(aToB) {
                scoresA.push(speech.cs);
                scoresB.push(NaN);
            }
            if(bToA) {
                scoresB.push(speech.cs);
                scoresA.push(NaN);
            }
            if(aToB || bToA) {
                numInteractions++;
                lines.push(speech.content);
                lineIndices.push(lineIndex);
            }
            lineIndex++;
        }
    }

    let averageScore = 0;
    for(let i = 0; i < scoresA.length; i++)
        averageScore += (scoresA[i] || 0) / scoresA.length;
    for(let i = 0; i < scoresB.length; i++)
        averageScore += (scoresB[i] || 0) / scoresB.length;

    // Reset display
    dom.characterInteractionsMeta.empty();
    dom.characterInteractionsGraph.empty()

    // Add message and stop displaying if there is no data to show
    if(numInteractions == 0) {
        dom.characterInteractionsMeta.append(
            $("<span>").html("No interactions.&nbsp;"),
            $("<span>").attr("data-feather", "frown")
        );
        feather.replace();
        return;
    }  
 
    // Add meta information
    dom.characterInteractionsMeta.append(
        $("<table>")
            .append($("<tr>")
                .append($("<td>").text("Number of adjacent dialogue lines*:"))
                .append($("<td>").text(Math.floor(numInteractions/2)))
            )
            .append($("<tr>")
                .append($("<td>").text("Average sentiment score:"))
                .append($("<td>").text(Math.round(averageScore*1000)/1000).css("color", getSentimentColor(averageScore)))
            )
    );

    // Display graph
    let canvas = $("<canvas>");
    let chartCtx = canvas[0].getContext("2d");
    dom.characterInteractionsGraph.append(canvas);

    new Chart(chartCtx, {
        type: "line",
        data: {
            labels: lineIndices,
            datasets: [
                {data: scoresA, label: "Compound sentiment score (" + nameA + ")", fill: false, borderColor: "rgba(180,60,80,0.3)"},
                {data: scoresB, label: "Compound sentiment score (" + nameB + ")", fill: false, borderColor: "rgba(60,140,180,0.3)"},
                {data: smoothMovingWindow(scoresA), label: "Compound sentiment score (" + nameA + "), smoothed", fill: false, borderColor: "rgb(180,60,80)"},
                {data: smoothMovingWindow(scoresB), label: "Compound sentiment score (" + nameB + "), smoothed", fill: false, borderColor: "rgb(60,140,180)"}
            ]
        },
        options: {
            responsive: true,
            spanGaps: true,
            title: {
                display: true,
                text: "Evolution of character sentiment for co-occurrences during the movie"
            },
            tooltips: {
                callbacks: {
                    title: (tooltipItem, data) => "",
                    label: (tooltipItem, data) => formatLabel(lines[tooltipItem.index])
                },
            }
        }
    });
}

function fillCharacterSelect(select, movie, minLinesThreshold) {
    select.empty();    for(let cname of movie.sortedCharacterNames) {
        let c = movie.characters[cname];
        if(c.line_count <= minLinesThreshold)
            continue;
        select.append($("<option>").text(c.name).attr("value", c.name));
    }
}

$(document).ready(() => {
    // Register listener on file selection input
    $("#movie-file-selection").change((d) => {
        let file = $("#movie-file-selection")[0].files[0];
        fr.readAsText(file);
    });

    // Register listener on character breakdown <select>
    dom.breakdownSelect.change(() => {
        showCharacterBreakdown(dom.breakdownSelect.val());
    });

    // Register listener on character interactions compute <button>
    dom.characterInteractionsCompute.click(() => {
        showCharacterInteractions(dom.characterInteractionsSelectA.val(), dom.characterInteractionsSelectB.val());
    });
});


function createDirectionSentimentChart(movie, container) {
    let canvas = $("<canvas>");
    container.empty().append(canvas);
    
    let chartCtx2d = canvas[0].getContext("2d");
    
    let lineIndices = [], lines = [], lineIndex = 0;
    let scores = [];

    for(let i = 0; i < movie.entries.length; i++) {
        let e = movie.entries[i];
        if(e.type == TYPE_DIRECTION) {
            lineIndices.push(lineIndex);
            scores.push(e.cs);
            lineIndex++;
            lines.push(e.content);
        }
    }

    new Chart(chartCtx2d, {
        type: "line",
        data: {
            labels: lineIndices,
            datasets: [
                {data: scores, label: "Sentiment score (compound)", fill: false}, 
                {data: smoothMovingWindow(scores), label: "Sentiment score (compound), smoothed", fill: false, borderColor: "rgb(60,140,180)"}
            ]
        },
        options: {
            responsive: true,
            title: {
                display: true,
                text: "Evolution of the sentiment of direction information over the course of the movie"
            },
            tooltips: {
                callbacks: {
                    title: (tooltipItem, data) => "",
                    label: (tooltipItem, data) => formatLabel(lines[tooltipItem.index])
                },
            }
        }
    });
}