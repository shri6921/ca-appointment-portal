document.addEventListener('DOMContentLoaded', () => {
    // Role selection toggle in registration form
    const roleOptions = document.querySelectorAll('.role-option');
    const caFields = document.getElementById('caFields');
    const roleInput = document.getElementById('selectedRole');

    if (roleOptions.length > 0) {
        roleOptions.forEach(option => {
            option.addEventListener('click', () => {
                roleOptions.forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                const role = option.getAttribute('data-role');
                if (roleInput) roleInput.value = role;
                
                if (caFields) {
                    if (role === 'ca') {
                        caFields.style.display = 'block';
                    } else {
                        caFields.style.display = 'none';
                    }
                }
            });
        });
    }

    // Modal logic for booking appointment
    const bookModal = document.getElementById('bookModal');
    const bookBtns = document.querySelectorAll('.btn-book-ca');
    const closeModalBtn = document.querySelector('.modal-close');
    const caIdInput = document.getElementById('modalCaId');
    const caNameDisplay = document.getElementById('modalCaName');

    if (bookBtns.length > 0 && bookModal) {
        bookBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const caId = btn.getAttribute('data-ca-id');
                const caName = btn.getAttribute('data-ca-name');
                if (caIdInput) caIdInput.value = caId;
                if (caNameDisplay) caNameDisplay.textContent = caName;
                bookModal.classList.add('active');
            });
        });

        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => {
                bookModal.classList.remove('active');
            });
        }

        window.addEventListener('click', (e) => {
            if (e.target === bookModal) {
                bookModal.classList.remove('active');
            }
        });
    }
});

// Real-time CA Search Filter
function filterCAs() {
    const searchVal = document.getElementById('caSearchInput').value.toLowerCase();
    const caCards = document.querySelectorAll('.ca-card');
    caCards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(searchVal)) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}

// Notifications Dropdown Toggle
function toggleNotifs() {
    const dropdown = document.getElementById('notifDropdown');
    if (dropdown) {
        dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
    }
}

async function markRead() {
    try {
        await fetch('/notifications/mark_read', { method: 'POST' });
        const badge = document.getElementById('notifBadge');
        if (badge) badge.style.display = 'none';
    } catch (err) {
        console.error(err);
    }
}

// AI Tax Assistant Bot Toggle
function toggleTaxBot() {
    const bot = document.getElementById('taxBotWindow');
    if (bot) {
        bot.style.display = bot.style.display === 'none' ? 'flex' : 'none';
    }
}

async function sendTaxQuery() {
    const input = document.getElementById('taxQueryInput');
    const query = input.value.trim();
    if (!query) return;

    const body = document.getElementById('taxBotBody');
    body.innerHTML += `<div style="text-align: right; margin-bottom: 0.5rem;"><span style="background: var(--accent-indigo); color: white; padding: 0.4rem 0.8rem; border-radius: 12px; font-size: 0.8rem; display: inline-block;">${query}</span></div>`;
    input.value = '';
    body.scrollTop = body.scrollHeight;

    try {
        const response = await fetch('/api/tax_assistant', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await response.json();
        const formattedReply = data.reply.replace(/\n/g, '<br>');
        body.innerHTML += `<div style="text-align: left; margin-bottom: 0.5rem;"><span style="background: rgba(255,255,255,0.08); color: var(--text-primary); padding: 0.5rem 0.8rem; border-radius: 12px; font-size: 0.8rem; display: inline-block; border: 1px solid var(--border-color);">${formattedReply}</span></div>`;
        body.scrollTop = body.scrollHeight;
    } catch (err) {
        console.error(err);
    }
}

// e-Sign Document Approval
async function approveDocument(docId) {
    if (!confirm('Are you sure you want to digitally sign & approve this audit document?')) return;
    try {
        const response = await fetch(`/document/${docId}/approve`, { method: 'POST' });
        const data = await response.json();
        if (response.ok && data.success) {
            alert('🎉 Document digitally signed and verified!');
            window.location.reload();
        } else {
            alert(data.error || 'Approval failed.');
        }
    } catch (err) {
        console.error(err);
        alert('Error approving document.');
    }
}

// Appointment Notes / Discussion Thread
async function sendAppointmentNote(appointmentId) {
    const input = document.getElementById(`noteInput_${appointmentId}`);
    if (!input) return;
    const text = input.value.strip ? input.value.strip() : input.value.trim();
    if (!text) return;

    try {
        const response = await fetch(`/appointment/${appointmentId}/note`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note: text })
        });
        const data = await response.json();
        if (response.ok && data.success) {
            window.location.reload();
        } else {
            alert(data.error || 'Failed to post note.');
        }
    } catch (err) {
        console.error(err);
        alert('Error posting note.');
    }
}

// Function for CA to update appointment status asynchronously
async function updateAppointmentStatus(appointmentId, status) {
    if (!confirm(`Are you sure you want to set status to '${status}'?`)) {
        return;
    }

    try {
        const response = await fetch(`/ca/appointment/${appointmentId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status })
        });

        const data = await response.json();
        if (response.ok && data.success) {
            window.location.reload();
        } else {
            alert(data.error || 'Failed to update appointment status.');
        }
    } catch (err) {
        console.error('Error:', err);
        alert('An error occurred while updating the status.');
    }
}

// Function for CA to set consultation fee
async function setAppointmentFee(appointmentId) {
    const feeStr = prompt('Enter Consultation Fee amount (in ₹):');
    if (feeStr === null) return;
    const fee = parseFloat(feeStr);
    if (isNaN(fee) || fee < 0) {
        alert('Please enter a valid amount.');
        return;
    }

    try {
        const response = await fetch(`/ca/appointment/${appointmentId}/fee`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fee_amount: fee })
        });

        const data = await response.json();
        if (response.ok && data.success) {
            window.location.reload();
        } else {
            alert(data.error || 'Failed to update fee.');
        }
    } catch (err) {
        console.error(err);
        alert('Error updating fee.');
    }
}

// Payment Modal logic
let activePayApptId = null;
function openPayModal(appointmentId, serviceName, feeAmount) {
    activePayApptId = appointmentId;
    document.getElementById('payServiceName').textContent = serviceName;
    document.getElementById('payAmountDisplay').textContent = `₹${parseFloat(feeAmount).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
    document.getElementById('payModal').classList.add('active');
}

function closePayModal() {
    document.getElementById('payModal').classList.remove('active');
}

async function submitPaymentSim() {
    if (!activePayApptId) return;
    const btn = document.getElementById('paySubmitBtn');
    btn.disabled = true;
    btn.textContent = 'Processing Payment...';

    setTimeout(async () => {
        try {
            const response = await fetch(`/customer/appointment/${activePayApptId}/pay`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            if (response.ok && data.success) {
                alert('🎉 Payment Successful! Receipt generated and CA notified.');
                window.location.reload();
            } else {
                alert(data.error || 'Payment failed.');
                btn.disabled = false;
                btn.textContent = 'Pay Now';
            }
        } catch (err) {
            console.error(err);
            alert('Error processing payment.');
            btn.disabled = false;
            btn.textContent = 'Pay Now';
        }
    }, 1200);
}

// Receipt Viewer
function viewReceipt(apptId, caName, clientName, serviceName, amount) {
    const content = `
    <html>
    <head><title>Payment Receipt #${apptId}</title>
    <style>
        body { font-family: sans-serif; padding: 2rem; color: #1e293b; }
        .receipt-card { border: 2px solid #6366f1; padding: 2rem; border-radius: 12px; max-width: 500px; margin: 0 auto; }
        h2 { color: #4f46e5; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; }
        .row { display: flex; justify-content: space-between; margin: 1rem 0; font-size: 1.1rem; }
        .total { font-size: 1.4rem; font-weight: bold; color: #10b981; border-top: 2px solid #e2e8f0; padding-top: 1rem; }
    </style>
    </head>
    <body>
        <div class="receipt-card">
            <h2>📜 CA FinConnect Payment Receipt</h2>
            <p><strong>Receipt ID:</strong> REC-2026-${apptId}</p>
            <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
            <hr>
            <div class="row"><span>Chartered Accountant:</span> <strong>${caName}</strong></div>
            <div class="row"><span>Client Name:</span> <strong>${clientName}</strong></div>
            <div class="row"><span>Service:</span> <strong>${serviceName}</strong></div>
            <div class="row total"><span>Total Paid:</span> <span>₹${parseFloat(amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span></div>
            <div style="text-align: center; margin-top: 2rem;">
                <button onclick="window.print()" style="background:#4f46e5; color:white; padding:0.6rem 1.2rem; border:none; border-radius:6px; cursor:pointer;">Print / Save PDF</button>
            </div>
        </div>
    </body>
    </html>
    `;
    const win = window.open('', '_blank');
    win.document.write(content);
    win.document.close();
}
