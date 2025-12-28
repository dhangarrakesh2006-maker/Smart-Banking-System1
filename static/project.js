// Minimal helper functions used by templates
function toggleMobile() {
	const nav = document.getElementById('navLinks');
	if (nav) nav.classList.toggle('open');
}

function loginDemo() {
	alert('This is a demo. Internet banking login is not implemented.');
}

function fakeLocate() {
	const loc = document.getElementById('loc');
	const list = document.getElementById('locList');
	if (!loc || !list) return;
	const input = loc.value.trim();
	list.innerHTML = '';
	if (!input) {
		list.innerHTML = '<li class="muted">Please enter a pincode or district name</li>';
		return;
	}

	// show loading
	list.innerHTML = '<li class="muted">Searching...</li>';

	// choose param: numeric input -> pincode, otherwise use free-text 'q'
	const isNumeric = /^[0-9]+$/.test(input);
	const url = isNumeric ? `/api/atms?pincode=${encodeURIComponent(input)}` : `/api/atms?q=${encodeURIComponent(input)}`;

	fetch(url)
		.then(r => {
			if (!r.ok) {
				// try to get text body for debugging
				return r.text().then(t => { throw {status: r.status, statusText: r.statusText, body: t}; });
			}
			// try to parse JSON; handle non-JSON gracefully
			return r.text().then(txt => {
				try {
					return JSON.parse(txt);
				} catch (e) {
					throw {status: r.status, statusText: r.statusText, body: txt || 'non-json response'};
				}
			});
		})
		.then(data => {
			if (data && data.error) {
				list.innerHTML = `<li class="muted">Error: ${data.error}</li>`;
				return;
			}
			if (!data || !data.atms || data.atms.length === 0) {
				list.innerHTML = '<li class="muted">No ATMs found for this pincode.</li>';
				return;
			}
			list.innerHTML = '';
			data.atms.forEach(a => {
				const li = document.createElement('li');
				li.innerHTML = `<strong>${a.name}</strong><br/><small class="muted">${a.address || ''} (Pincode: ${a.pincode})</small>`;
				list.appendChild(li);
			});
		})
		.catch(err => {
			console.error('ATM lookup error', err);
			if (err && err.status) {
				// HTTP error or non-JSON response
				list.innerHTML = `<li class="muted">Server error: ${err.status} ${err.statusText || ''} - ${String(err.body || '').slice(0,200)}</li>`;
				return;
			}
			// network-level error
			list.innerHTML = '<li class="muted">Cannot reach server. Is the Flask app running? Try starting the server (python -m flask run).</li>';
		});
}

// Expose to global scope for inline handlers
window.toggleMobile = toggleMobile;
window.loginDemo = loginDemo;
window.fakeLocate = fakeLocate;

// Simple client-side language switching
const translations = {
	en: {
		internetBanking: 'Internet Banking',
		openAccount: 'Open Account',
		heroTitle: 'Smart banking for everyday India',
		heroSubtitle: 'Accounts, cards, payments, deposits and loans — all in one secure dashboard. No backend here, this is a purely front-end educational demo.',
		emailLabel: 'Email',
		passwordLabel: 'Password / MPIN',
	},
	mr: {
		internetBanking: 'इंटरनेट बँकिंग',
		openAccount: 'खाते उघडा',
		heroTitle: 'दररोजच्या व्यवहारांसाठी स्मार्ट बँकिंग',
		heroSubtitle: 'खातं, कार्ड्स, पेमेंट, एफडी व कर्ज — सर्व एका सुरक्षित डॅशबोर्डवर. येथे फक्त डेमो आहे.',
		emailLabel: 'ईमेल',
		passwordLabel: 'पासवर्ड / एमपीआयएन',
	}
};

function applyLanguage(lang) {
	const t = translations[lang] || translations.en;
	const internetBtn = document.getElementById('internetBtn');
	const openBtn = document.getElementById('openAccountBtn');
	const heroTitle = document.getElementById('heroTitle');
	const heroSubtitle = document.getElementById('heroSubtitle');
	const labelEmail = document.getElementById('labelEmail');
	const labelPassword = document.getElementById('labelPassword');
	if (internetBtn) internetBtn.textContent = t.internetBanking;
	if (openBtn) openBtn.textContent = t.openAccount;
	if (heroTitle) heroTitle.textContent = t.heroTitle;
	if (heroSubtitle) heroSubtitle.textContent = t.heroSubtitle;
	if (labelEmail) labelEmail.textContent = t.emailLabel;
	if (labelPassword) labelPassword.textContent = t.passwordLabel;
}

function switchLang() {
	const sel = document.getElementById('langSel');
	if (!sel) return;
	const lang = sel.value || 'en';
	applyLanguage(lang);
}

window.switchLang = switchLang;
