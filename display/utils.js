
// Colors used for displaying sentiment information
let red = [220, 70, 60],
    grey = [180, 180, 180],
    green = [50, 170, 30];

/**
 * Get the color associated to a given sentiment score, on a continuum from red (-1) to grey (0) to green (+1).
 * @param {float} compoundScore - A score in the range [-1, 1]
 * @return {String} the color corresponding to the given score on the continuum. 
 */
function getSentimentColor(compoundScore) {
    let f = Math.pow(Math.abs(compoundScore), 0.4); // exponential color grading
    let colorArray = compoundScore > 0 ? interpolateColor(grey, green, f) : interpolateColor(grey, red, f)
    return "rgb(" + colorArray.join(",") + ")";
}

/**
 * Interpolate between two colors at a given point.
 * @param {Array} c1 - A color in [r, g, b] format 
 * @param {Array} c2 - Another color in [r, g, b] format 
 * @param {float} f - A float in the range [0,1] 
 * @return {Array} the interpolated color
 */
function interpolateColor(c1, c2, f) { 
    return [
        Math.floor(c1[0]*(1-f) + c2[0]*f),
        Math.floor(c1[1]*(1-f) + c2[1]*f),
        Math.floor(c1[2]*(1-f) + c2[2]*f)
    ];
}

/**
 * Smooths the given data array using an averaging moving window strategy.
 * @param {Array} data - An array of numeric data 
 * @param {int} [windowSize=data.length / 5] - The size of the moving window (number of sample before current sample).
 * @return {Array} the smoothed data, always the same length as the given array
 */
function smoothMovingWindow(data, windowSize) {
    if(windowSize === undefined)
        windowSize = Math.round(data.length / 5)
    if(windowSize <= 1)
        return data 

    out = []
    for(let i = 0; i < data.length; i++) {
        let praticalWindowSize = 0;
        let sum = 0;
        if(Number.isNaN(data[i]))
            out.push(NaN);
        else {
            // Calculate the average in the moving window
            for(let j = i - windowSize; j <= i; j++) {
                idx = Math.abs(j);
                if(!Number.isNaN(data[idx])) {
                    praticalWindowSize++;
                    sum += data[idx];
                }
            }
            out.push(sum / praticalWindowSize);
        }
    }
    return out;
}

/**
 * Get the name of the character who speaks after the one at a given index, within a scene.
 * @param {Object} movie - A movie object 
 * @param {int} i - The index of an entry in the parsed movie.
 * @return {String} the name of the next character, or null if no character comes after in the scene.
 */
function getNextCharacter(movie, i) {
    let originalCharacter = movie.entries[i].content;
    do {
        i++;
    }
    while(i < movie.entries.length-1 && (movie.entries[i].type != TYPE_CHARACTER || movie.entries[i].content == originalCharacter) && movie.entries[i].type != TYPE_LOCATION);
    return movie.entries[i].type == TYPE_CHARACTER ? movie.entries[i].content : null;
}

/**
 * Get the name of the character who speaks before the one at a given index, within a scene.
 * @param {Object} movie - A movie object 
 * @param {int} i - The index of an entry in the parsed movie.
 * @return {String} the name of the previous character, or null if no character comes before in the scene.
 */
function getPreviousCharacter(movie, i) {
    let originalCharacter = movie.entries[i].content;
    do {
        i--;
    }
    while(i > 0 && (movie.entries[i].type != TYPE_CHARACTER || movie.entries[i].content == originalCharacter) && movie.entries[i].type != TYPE_LOCATION);
    return movie.entries[i].type == TYPE_CHARACTER ? movie.entries[i].content : null;
}

/**
 * Format text for labelling graphs so it fits a length limit.
 * @param {String} text - Some text
 * @return {String} the formatted text.
 */
function formatLabel(text) {
    let labelLimit = 100;
    if(text.length > labelLimit)
        text = text.substring(0, labelLimit) + "...";
    return text;
}

/**
 * Format text for the title of a graph label.
 * @param {Object} tooltipItem - The tooltip item provided by chart.js
 * @return {String} the formatted text.
 */
function formatLabelTitle(tooltipItem) {
    return Math.round(parseFloat(tooltipItem[0].value)*1000)/1000;
}