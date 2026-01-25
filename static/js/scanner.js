let lastScanTime = 0;

function onScanSuccess(decodedText, decodedResult) {
    let now = Date.now();
    if(now - lastScanTime < 2000){
        // wait 2 seconds between scans
        return;
    }
    lastScanTime = now;
    processScan(decodedText);
}

function manualEntry(){
    let code = document.getElementById("manual-code").value;
    processScan(code);
}

function processScan(code){
    fetch("/worker/manual_entry", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({pass_code: code})
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("scan-result").innerText = data.message + (data.remaining_uses!==undefined ? ", Remaining: "+data.remaining_uses : "");
    });
}

let html5QrcodeScanner = new Html5QrcodeScanner(
    "scanner", { fps:10, qrbox:250 });
html5QrcodeScanner.render(onScanSuccess);
