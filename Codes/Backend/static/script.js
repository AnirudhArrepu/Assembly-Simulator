document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("run-button").addEventListener("click", runProgram);
});

function runProgram() {
    const programInput = document.getElementById("program-input").value;
    const consoleOutput = document.getElementById("displayed-output");
    // const registerValues = document.getElementById("register-values");

    // if (!registerValues) {
    //     console.error("Error: #register-values element not found!");
    //     return;
    // }

    consoleOutput.value = "";
    // registerValues.innerHTML = "";

    console.log("Sending program:", programInput);

    fetch("http://127.0.0.1:5000/simulate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ program: programInput }),
    })
        .then((response) => response.json())
        .then((data) => {
            consoleOutput.value = `Clock cycles: ${data.clock}\n\n`;

            // ✅ Display memory values
            const memoryOutput = `
                Memory 1: ${data.memory1}
                Memory 2: ${data.memory2}
                Memory 3: ${data.memory3}
                Memory 4: ${data.memory4}
            `.trim();
            consoleOutput.value += `${memoryOutput}\n\n`;

            // ✅ Display register values for all cores
            const cores = ["core0", "core1", "core2", "core3"];
            cores.forEach((core) => {
                if (data[core]) {
                    const coreDiv = document.createElement("div");
                    coreDiv.className = "register";
                    coreDiv.innerHTML = `<strong>${core}</strong><br>${Object.entries(
                        data[core]
                    )
                        .map(([key, value]) => `${key}: ${value}`)
                        .join("<br>")}`;
                    // registerValues.appendChild(coreDiv);
                }
            });
        })
        .catch((error) => {
            console.error("Error:", error);
            consoleOutput.value = "Error: Unable to connect to the server.";
        });
}
