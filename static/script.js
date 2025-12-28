function loader(){
    document.querySelector('.loader-container').classList.add('fade-out');
}

function fadeOut(){
    setInterval(loader,2000);
}
// Fetch current user info from Flask
function loadUserInfo() {
    fetch('/api/current-user')
        .then(response => {
            if (!response.ok) {
                if (response.status === 401) {
                    // Not logged in, redirect to home
                    window.location.href = '/';
                    return;
                }
                throw new Error('Failed to fetch user info');
            }
            return response.json();
        })
        .then(data => {
            if (data && data.user) {
                document.getElementById('userName').textContent = data.user.name.toUpperCase();
                const balance = parseFloat(data.user.balance || 0).toFixed(2);
                document.getElementById('balance').textContent = `₹${parseFloat(balance).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                document.getElementById('currentBalance').textContent = `Current Balance ₹${parseFloat(balance).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }
        })
        .catch(error => {
            console.error('Error loading user info:', error);
        });
}

// Load user info when page loads
window.addEventListener('load', loadUserInfo);
window.onload = fadeOut;
