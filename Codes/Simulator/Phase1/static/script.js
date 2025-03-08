document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("run-button").addEventListener("click", runProgram);
});

function runProgram() {
    const programInput = document.getElementById("program-input").value;
    const consoleOutput = document.getElementById("displayed-output");
    const registerTableBody = document.querySelector(".register-table tbody");

    if (!registerTableBody) {
        console.error("Error: Register table not found!");
        return;
    }

    consoleOutput.value = "";
    registerTableBody.innerHTML = ""; // Clear previous values

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
            consoleOutput.value = `Clock cycles: ${data.clock}\n\nCore0Reg: ${data.core0}\n\nCore1Reg: ${data.core1}\n\nCore2Reg: ${data.core2}\n\nCore3Reg: ${data.core3}\n\n Memory1: ${data.memory1}\n\nMemory2: ${data.memory2}\n\nMemory3: ${data.memory3}\n\nMemory4: ${data.memory4}\n\n`;

            // ✅ Show register values for core0
            if (data.core0) {
                Object.entries(data.core0).forEach(([register, value]) => {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>x${register}</td>
                        <td>${getAlias(register)}</td>
                        <td>${formatHex(value)}</td>
                    `;
                    registerTableBody.appendChild(row);
                });
            } else {
                console.error("Error: core0 register data not found!");
            }
        })
        .catch((error) => {
            console.error("Error:", error);
            consoleOutput.value = "Error: Unable to connect to the server.";
        });
}

// ✅ Function to map register names to aliases
function getAlias(register) {
    const aliasMap = {
        0: "zero",
        1: "ra",
        2: "sp",
        3: "gp",
        4: "tp",
        5: "t0",
        6: "t1",
        7: "t2",
        8: "s0",
        9: "s1",
        10: "a0",
        11: "a1",
        12: "a2",
        13: "a3",
        14: "a4",
        15: "a5",
        16: "a6",
        17: "a7",
        18: "s2",
        19: "s3",
        20: "s4",
        21: "s5",
        22: "s6",
        23: "s7",
        24: "s8",
        25: "s9",
        26: "s10",
        27: "s11",
        28: "t3",
        29: "t4",
        30: "t5",
        31: "t6"
    };
    
    return aliasMap[register] || "-";
}

// ✅ Function to format register values as hexadecimal (0x...)
function formatHex(value) {
    if (typeof value === "number") {
        return `0x${value.toString(16).padStart(8, '0')}`;
    }
    return value; // If it's already formatted correctly, return as is
}
