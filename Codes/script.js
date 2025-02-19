document.getElementById('run-button').addEventListener('click', runProgram);

function runProgram() {
    const programInput = document.getElementById('program-input').value;
    const consoleOutput = document.getElementById('displayed-output');
    const registerValues = document.getElementById('register-values');

    // Clear previous console output and register values
    consoleOutput.value = '';
    registerValues.innerHTML = '';

    // Send the program input to the Flask server
    fetch('http://127.0.0.1:5000/run', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ program: programInput })
    })
    .then(response => response.json())
    .then(data => {
        // Display the result in the console
        consoleOutput.value = `Clock cycles: ${data.clock}\n\nMemory: ${data.memory.join(', ')}\n\n`;

        // Display the register values
        for (const core in data.registerStates) {
            const coreDiv = document.createElement('div');
            coreDiv.className = 'register';
            coreDiv.innerHTML = `<strong>${core}</strong><br>${data.registerStates[core].join(', ')}`;
            registerValues.appendChild(coreDiv);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}