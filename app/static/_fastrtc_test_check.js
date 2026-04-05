
        const chatWindow = document.getElementById("chat-window");
        const input = document.getElementById("user-input");
        const sendBtn = document.getElementById("send-btn");
        const micBtn = document.getElementById("mic-btn");
        const remoteAudio = document.getElementById("remote-audio");
        const statusDot = document.getElementById("status-dot");
        const statusText = document.getElementById("status-text");
        const healthValue = document.getElementById("health-value");
        const rtcState = document.getElementById("rtc-state");
        const dashTTFT = document.getElementById("dash-ttft");
        const dashTPS = document.getElementById("dash-tps");

        let chatHistory = [];
        let peerConnection = null;
        let localStream = null;
        let rtcConnecting = false;

        function appendBubble(role, text) {
            const div = document.createElement("div");
            div.className = `bubble ${role}`;
            div.textContent = text;
            chatWindow.appendChild(div);
            chatWindow.scrollTop = chatWindow.scrollHeight;
            return div;
        }

        function setStatus(text, color) {
            statusText.textContent = text;
            statusDot.style.background = color;
            statusDot.style.boxShadow = `0 0 16px ${color}`;
        }

        function setRtcStateText(text) {
            rtcState.textContent = text;
        }

        async function checkStatus() {
            try {
                const response = await fetch("/health");
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                healthValue.textContent = data.status;
                setStatus(`READY - ${data.app}`, "#22c55e");
            } catch (error) {
                healthValue.textContent = "offline";
                setStatus("OFFLINE", "#ef4444");
            }
        }

        function cleanupRtcResources() {
            if (localStream) {
                localStream.getTracks().forEach((track) => track.stop());
                localStream = null;
            }

            if (remoteAudio.srcObject) {
                remoteAudio.srcObject = null;
            }
        }

        function stopRtc() {
            if (peerConnection) {
                if (peerConnection.getTransceivers) {
                    peerConnection.getTransceivers().forEach((transceiver) => {
                        if (transceiver.stop) {
                            transceiver.stop();
                        }
                    });
                }

                if (peerConnection.getSenders) {
                    peerConnection.getSenders().forEach((sender) => {
                        if (sender.track) {
                            sender.track.stop();
                        }
                    });
                }

                peerConnection.close();
            }

            peerConnection = null;
            rtcConnecting = false;
            cleanupRtcResources();
            micBtn.classList.remove("active");
            micBtn.textContent = "开始回声测试";
            setRtcStateText("idle");
            setStatus("READY - Echo stopped", "#22c55e");
        }

        async function startRtc() {
            if (rtcConnecting || peerConnection) {
                return;
            }

            rtcConnecting = true;
            micBtn.disabled = true;
            setRtcStateText("connecting");
            setStatus("RTC CONNECTING...", "#f59e0b");

            try {
                localStream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: false
                    }
                });

                const pc = new RTCPeerConnection();
                const webrtcId = Math.random().toString(36).slice(2);
                peerConnection = pc;

                localStream.getTracks().forEach((track) => {
                    pc.addTrack(track, localStream);
                });

                pc.addEventListener("track", (event) => {
                    if (remoteAudio.srcObject !== event.streams[0]) {
                        remoteAudio.srcObject = event.streams[0];
                        remoteAudio.play().catch(() => {});
                    }
                });

                pc.addEventListener("connectionstatechange", () => {
                    const state = pc.connectionState || "unknown";
                    setRtcStateText(state);

                    if (state === "connected") {
                        micBtn.classList.add("active");
                        micBtn.textContent = "停止回声测试";
                        setStatus("RTC CONNECTED", "#22c55e");
                    } else if (state === "failed" || state === "disconnected" || state === "closed") {
                        stopRtc();
                    }
                });

                pc.createDataChannel("text");

                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);

                const response = await fetch("/voice/webrtc/offer", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        sdp: offer.sdp,
                        type: offer.type,
                        webrtc_id: webrtcId
                    })
                });

                if (!response.ok) {
                    throw new Error(`FastRTC offer failed: ${response.status}`);
                }

                const answer = await response.json();
                await pc.setRemoteDescription(answer);

                appendBubble("ai", "FastRTC 回声测试已启动。现在可以对着麦克风讲话，若听到自己的声音返回，就说明实现成功。");
            } catch (error) {
                stopRtc();
                appendBubble("ai", `FastRTC 连接失败：${error.message}`);
                setRtcStateText("error");
                setStatus("RTC ERROR", "#ef4444");
            } finally {
                rtcConnecting = false;
                micBtn.disabled = false;
            }
        }

        async function toggleRtc() {
            if (peerConnection || rtcConnecting) {
                stopRtc();
                return;
            }

            await startRtc();
        }

        async function postMessage() {
            const text = input.value.trim();
            if (!text) {
                return;
            }

            appendBubble("user", text);
            input.value = "";
            input.disabled = true;
            sendBtn.disabled = true;

            const startTime = performance.now();
            let ttftTime = null;
            let tokenCount = 0;

            const aiBubble = appendBubble("ai", "...");
            const statsArea = document.createElement("div");
            statsArea.className = "timing";
            aiBubble.appendChild(statsArea);

            try {
                const response = await fetch("/api/v1/interview/chat/stream", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        message: text,
                        history: chatHistory
                    })
                });

                if (!response.ok || !response.body) {
                    throw new Error(`Chat stream failed: ${response.status}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let fullContent = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        break;
                    }

                    const chunk = decoder.decode(value);
                    if (!chunk) {
                        continue;
                    }

                    if (ttftTime === null && chunk.trim()) {
                        ttftTime = performance.now();
                        const ttft = Math.round(ttftTime - startTime);
                        dashTTFT.textContent = `${ttft} ms`;
                        statsArea.innerHTML = `TTFT: <b>${ttft} ms</b>`;
                    }

                    if (fullContent === "...") {
                        aiBubble.firstChild.textContent = "";
                        fullContent = "";
                    }

                    fullContent += chunk;
                    tokenCount += 1;
                    aiBubble.firstChild.textContent = fullContent;
                    chatWindow.scrollTop = chatWindow.scrollHeight;

                    if (ttftTime) {
                        const elapsed = (performance.now() - ttftTime) / 1000;
                        if (elapsed > 0.1) {
                            dashTPS.textContent = `${(tokenCount / elapsed).toFixed(1)} t/s`;
                        }
                    }
                }

                const totalTime = Math.round(performance.now() - startTime);
                const ttftLabel = ttftTime ? `${Math.round(ttftTime - startTime)} ms` : "--";
                statsArea.innerHTML = `TTFT: <b>${ttftLabel}</b> | Total: <b>${totalTime} ms</b>`;
                chatHistory.push(
                    { role: "user", content: text },
                    { role: "assistant", content: aiBubble.firstChild.textContent }
                );
            } catch (error) {
                aiBubble.firstChild.textContent = `Error: ${error.message}`;
            } finally {
                input.disabled = false;
                sendBtn.disabled = false;
                input.focus();
            }
        }

        checkStatus();
        micBtn.addEventListener("click", toggleRtc);
        sendBtn.addEventListener("click", postMessage);
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                postMessage();
            }
        });
        window.addEventListener("beforeunload", stopRtc);
    