const API_BASE = '${BACKEND_URL}';

// Anti-Reload Guard
window.onbeforeunload = function() {
    if (document.getElementById('generate-btn').disabled) {
        return "Generation in progress, are you sure?";
    }
};

async function generate() {
    const user = document.getElementById('username').value.trim();
    if (!user) return alert("Please enter a username");

    // UI Elements
    const btn = document.getElementById('generate-btn');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result-container');
    const inputDiv = document.getElementById('input-section');
    const errorDiv = document.getElementById('error-display');
    const cardMount = document.getElementById('card-mount');

    // 1. Lock UI
    btn.disabled = true;
    errorDiv.style.display = 'none';
    statusDiv.style.display = 'block';
    
    try {
        updateStep(1, 'active');
        
        const theme = document.getElementById('theme').value;
        const prompt = `Generate a dev card for ${user} with ${theme} theme.`;

        const response = await fetch(`${API_BASE}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, prompt })
        });

        if (!response.ok) throw new Error("Backend failed. Check terminal.");

        updateStep(1, 'done');
        updateStep(2, 'active');
        
        const data = await response.json();
        
        updateStep(2, 'done');
        updateStep(3, 'active');

        // 2. Inject Content
        cardMount.innerHTML = data.html;
        const finalUrl = data.card_url.startsWith('http') ? data.card_url : `${API_BASE}${data.card_url}`;
        document.getElementById('url-val').innerText = finalUrl;
        document.getElementById('link-direct').href = finalUrl;
        
        // 3. FORCE VISIBILITY
        inputDiv.style.display = 'none';
        resultDiv.style.display = 'block';
        
        console.log("SUCCESS: UI should now show resultDiv");
        
        // 4. Download handler
        document.getElementById('download-btn').onclick = async () => {
            const el = document.getElementById('github-card');
            const canvas = await html2canvas(el, { useCORS: true, scale: 2 });
            const link = document.createElement('a');
            link.download = `card-${user}.png`;
            link.href = canvas.toDataURL();
            link.click();
        };

    } catch (err) {
        console.error(err);
        errorDiv.innerText = "Error: " + err.message;
        errorDiv.style.display = 'block';
        statusDiv.style.display = 'none';
        btn.disabled = false;
    }
}

function updateStep(id, status) {
    const el = document.getElementById('step-' + id);
    if (el) {
        if (status === 'active') el.style.color = '#58a6ff';
        if (status === 'done') {
            el.style.color = '#2ea043';
            el.innerText = '✓ ' + el.innerText.substring(2);
        }
    }
}

function copyLink() {
    const url = document.getElementById('url-val').innerText;
    navigator.clipboard.writeText(url);
    alert("URL Copied to clipboard!");
}

// Global scope access for HTML onclick
window.generate = generate;
window.copyLink = copyLink;

// Handle Enter Key
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('username').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            generate();
        }
    });
});
