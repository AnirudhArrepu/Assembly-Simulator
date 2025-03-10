document.addEventListener("DOMContentLoaded", function() {
    const runButton = document.getElementById("run-button");
    const programInput = document.getElementById("program-input");
    const displayedOutput = document.getElementById("displayed-output");
    const dataForwardingCheckbox = document.getElementById("data-forwarding");
    const registerTableBody = document.querySelector(".register-table tbody");

    runButton.addEventListener("click", function() {
        const program = programInput.value;
        const dataForwarding = dataForwardingCheckbox.checked;
        const latencies = getLatencies();

        runProgram(program, dataForwarding, latencies);
    });

    function getLatencies() {
        const latencyInputs = document.querySelectorAll("input[id^='latency-']");
        const latencies = {};
        latencyInputs.forEach(input => {
            const instruction = input.id.replace('latency-', '');
            latencies[instruction] = parseInt(input.value) || 0;
        });
        return latencies;
    }

    function runProgram(program, dataForwarding, latencies) {
        displayedOutput.value = "Executing program...";

        fetch("http://127.0.0.1:5000/simulate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                program: program,
                forwarding: dataForwarding,
                latencies: latencies
            }),
        })
        .then(response => response.json())
        .then(data => {
            displayedOutput.value = `Clock cycles: ${data.clock}\n\n`;

            for (let i = 0; i < 4; i++) {
                if (data[`core${i}`]) {
                    displayedOutput.value += `Core${i} Registers:\n${JSON.stringify(data[`core${i}`], null, 2)}\n\n`;
                }
            }

            displayedOutput.value += `Shared Memory:\n${JSON.stringify(data.memory, null, 2)}\n\n`;

            updateRegisterTable(data.core0);  // Update the UI table with core0 register values
        })
        .catch(error => {
            console.error("Error:", error);
            displayedOutput.value = "Error: Unable to connect to the server.";
        });
    }

    function updateRegisterTable(coreRegisters) {
        registerTableBody.innerHTML = ""; // Clear previous entries

        if (coreRegisters) {
            Object.entries(coreRegisters).forEach(([register, value]) => {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>x${register}</td>
                    <td>${getAlias(register)}</td>
                    <td>${formatHex(value)}</td>
                `;
                registerTableBody.appendChild(row);
            });
        }
    }

    function getAlias(register) {
        const aliasMap = {
            0: "zero", 1: "ra", 2: "sp", 3: "gp", 4: "tp", 5: "t0", 6: "t1", 7: "t2",
            8: "s0", 9: "s1", 10: "a0", 11: "a1", 12: "a2", 13: "a3", 14: "a4", 15: "a5",
            16: "a6", 17: "a7", 18: "s2", 19: "s3", 20: "s4", 21: "s5", 22: "s6", 23: "s7",
            24: "s8", 25: "s9", 26: "s10", 27: "s11", 28: "t3", 29: "t4", 30: "t5", 31: "t6"
        };
        return aliasMap[register] || "-";
    }

    function formatHex(value) {
        return typeof value === "number" ? `0x${value.toString(16).padStart(8, '0')}` : value;
    }
});
