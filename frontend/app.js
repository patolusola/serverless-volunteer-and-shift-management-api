const API_URL = 'https://o80f898rp7.execute-api.eu-west-2.amazonaws.com';

function setStatus(elementId, message, type) {
    const el = document.getElementById(elementId);
    el.className = `status ${type}`;
    el.innerText = message;
}

// check existing session on load
window.addEventListener('DOMContentLoaded', () => {
    const session = sessionStorage.getItem('user_session');
    if (session) {
        const user = JSON.parse(session);
        showDashboard(user);
    }
});

async function login() {
    const staffId = document.getElementById('loginStaffId').value.trim();
    const password = document.getElementById('loginPassword').value;

    if (!staffId || !password) {
        setStatus('loginStatus', 'Please enter Staff ID and password.', 'error');
        return;
    }

    setStatus('loginStatus', 'Authenticating...', 'loading');

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ staff_id: staffId, password: password })
        });
        const result = await response.json();

        if (!response.ok) {
            setStatus('loginStatus', result.error || 'Invalid credentials.', 'error');
            return;
        }

        sessionStorage.setItem('user_session', JSON.stringify(result));
        showDashboard(result);
    } catch (error) {
        setStatus('loginStatus', 'Network error during login.', 'error');
    }
}

function logout() {
    sessionStorage.removeItem('user_session');
    document.getElementById('dashboardView').classList.add('hidden');
    document.getElementById('loginView').classList.remove('hidden');
    document.getElementById('loginStaffId').value = '';
    document.getElementById('loginPassword').value = '';
    setStatus('loginStatus', '', '');
}

function showDashboard(user) {
    document.getElementById('loginView').classList.add('hidden');
    document.getElementById('dashboardView').classList.remove('hidden');

    document.getElementById('welcomeTitle').innerText = `Welcome, ${user.full_name}`;
    document.getElementById('userRoleBadge').innerText = `Role: ${user.role} | Staff ID: ${user.staff_id}`;

    if (user.role !== 'ADMIN') {
        document.getElementById('shiftStaffId').value = user.staff_id;
        document.getElementById('shiftStaffId').readOnly = true;
        document.getElementById('adminSection').classList.add('hidden');
        document.getElementById('rosterCard').classList.add('hidden');
        document.getElementById('shiftsTableHeader').innerText = 'My Shift History';
    } else {
        document.getElementById('adminSection').classList.remove('hidden');
        document.getElementById('rosterCard').classList.remove('hidden');
        document.getElementById('shiftsTableHeader').innerText = 'All Logged Shifts (Admin Master View)';
    }

    loadDashboardData(user);
}

async function addStaff() {
    const id = document.getElementById('staffId').value.trim();
    const name = document.getElementById('staffName').value.trim();
    const role = document.getElementById('staffRole').value.trim();
    const password = document.getElementById('staffPassword').value.trim();

    if (!id || !name || !role || !password) {
        setStatus('staffStatus', 'All fields are required to register staff.', 'error');
        return;
    }

    setStatus('staffStatus', 'Registering...', 'loading');

    try {
        const response = await fetch(`${API_URL}/volunteers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ staff_id: id, full_name: name, role: role, password: password })
        });
        const result = await response.json();

        if (!response.ok) {
            setStatus('staffStatus', result.error || 'Error registering staff.', 'error');
            return;
        }

        setStatus('staffStatus', result.message, 'success');
        document.getElementById('staffId').value = '';
        document.getElementById('staffName').value = '';
        document.getElementById('staffRole').value = '';
        document.getElementById('staffPassword').value = '';
        loadDashboardData(JSON.parse(sessionStorage.getItem('user_session')));
    } catch (error) {
        setStatus('staffStatus', 'Network error.', 'error');
    }
}

async function logShift() {
    const session = JSON.parse(sessionStorage.getItem('user_session'));
    const volId = session.role === 'ADMIN' ? document.getElementById('shiftStaffId').value.trim() : session.staff_id;
    const date = document.getElementById('shiftDate').value;
    const shiftType = document.getElementById('shiftType').value;
    const hours = document.getElementById('shiftHours').value;
    const status = document.getElementById('shiftStatusSelect').value;

    if (!volId || !date || !hours) {
        setStatus('shiftStatus', 'Please enter all required shift fields.', 'error');
        return;
    }

    setStatus('shiftStatus', 'Logging shift...', 'loading');

    try {
        const response = await fetch(`${API_URL}/shifts/log`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ staff_id: volId, date: date, shift_type: shiftType, hours: Number(hours), status: status })
        });
        const result = await response.json();

        if (!response.ok) {
            setStatus('shiftStatus', result.error || 'Error logging shift.', 'error');
            return;
        }

        setStatus('shiftStatus', result.message, 'success');
        if(session.role === 'ADMIN') document.getElementById('shiftStaffId').value = '';
        document.getElementById('shiftHours').value = '';
        loadDashboardData(session);
    } catch (error) {
        setStatus('shiftStatus', 'Network error logging shift.', 'error');
    }
}

async function loadDashboardData(user) {
    try {
        let shiftsUrl = `${API_URL}/shifts`;
        if (user.role !== 'ADMIN') {
            shiftsUrl += `?staff_id=${user.staff_id}`;
        }

        const [staffRes, shiftsRes] = await Promise.all([
            user.role === 'ADMIN' ? fetch(`${API_URL}/volunteers`) : Promise.resolve(null),
            fetch(shiftsUrl)
        ]);

        if (staffRes && staffRes.ok) {
            const staffData = await staffRes.json();
            const volunteers = staffData.volunteers || [];
            const staffBody = document.getElementById('staffTableBody');
            staffBody.innerHTML = volunteers.length === 0 ? '<tr><td colspan="4" class="empty-msg">No staff registered.</td></tr>' :
                volunteers.map(v => `
                    <tr>
                        <td>${v.staff_id}</td>
                        <td>${v.full_name}</td>
                        <td>${v.role}</td>
                        <td>
                            <button onclick="toggleStaffStatus('${v.staff_id}', ${v.is_active === false ? 'true' : 'false'})" style="padding: 6px 12px; margin:0; background-color: ${v.is_active === false ? '#22c55e' : '#ef4444'}; color: white; font-size: 12px; width: auto;">
                                ${v.is_active === false ? 'Activate' : 'Deactivate'}
                            </button>
                        </td>
                    </tr>
                `).join('');
        }

        if (staffRes && staffRes.ok) {
            const staffData = await staffRes.json();
            const volunteers = staffData.volunteers || [];
            const staffBody = document.getElementById('staffTableBody');
            staffBody.innerHTML = volunteers.length === 0 ? '<tr><td colspan="4" class="empty-msg">No staff registered.</td></tr>' :
                volunteers.map(v => `
                    <tr>
                        <td>${v.staff_id}</td>
                        <td>${v.full_name}</td>
                        <td>${v.role}</td>
                        <td>
                            <button onclick="resetStaffPassword('${v.staff_id}')" style="padding: 4px 8px; margin:0 4px 0 0; background-color: #3b82f6; color: white; font-size: 11px; width: auto;">Reset Pwd</button>
                            <button onclick="toggleStaffStatus('${v.staff_id}', ${v.is_active === false ? 'true' : 'false'})" style="padding: 4px 8px; margin:0; background-color: ${v.is_active === false ? '#22c55e' : '#ef4444'}; color: white; font-size: 11px; width: auto;">
                                ${v.is_active === false ? 'Activate' : 'Deactivate'}
                            </button>
                        </td>
                    </tr>
                `).join('');
        }

        if (shiftsRes.ok) {
            const shiftsData = await shiftsRes.json();
            const shifts = shiftsData.shifts || [];
            const shiftsBody = document.getElementById('shiftsTableBody');
            shiftsBody.innerHTML = shifts.length === 0 ? '<tr><td colspan="7" class="empty-msg">No shifts found.</td></tr>' :
                shifts.map(s => `<tr><td>${s.staff_id}</td><td>${s.full_name}</td><td>${s.role}</td><td>${s.date}</td><td>${s.shift_type}</td><td>${s.hours}</td><td>${s.status}</td></tr>`).join('');
        }
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

async function toggleStaffStatus(staffId, makeActive) {
    try {
        const response = await fetch(`${API_URL}/volunteers/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ staff_id: staffId, is_active: makeActive })
        });
        const result = await response.json();
        if (response.ok) {
            alert(result.message);
            loadDashboardData(JSON.parse(sessionStorage.getItem('user_session')));
        } else {
            alert(result.error || 'Failed to update status.');
        }
    } catch (err) {
        alert('Network error updating status.');
    }
}

async function resetStaffPassword(staffId) {
    const newPassword = prompt(`Enter a new temporary password for staff ${staffId}:`);
    if (!newPassword) return;

    try {
        const response = await fetch(`${API_URL}/volunteers/password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ staff_id: staffId, password: newPassword })
        });
        const result = await response.json();
        if (response.ok) {
            alert(result.message);
        } else {
            alert(result.error || 'Failed to reset password.');
        }
    } catch (err) {
        alert('Network error resetting password.');
    }
}