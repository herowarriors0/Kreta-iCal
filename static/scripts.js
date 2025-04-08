document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById("editModal");
    const closeBtn = document.querySelector(".close");
    const cancelBtn = document.querySelector(".cancel-btn");

    if (modal && closeBtn && cancelBtn) {
        flatpickr("#edit_date", {
            locale: "hu",
            dateFormat: "Y-m-d",
            minDate: "today",
            altInput: true,
            altFormat: "Y. F j.",
        });

        function closeModal() {
            modal.style.display = "none";
        }

        closeBtn.onclick = closeModal;
        cancelBtn.onclick = closeModal;
        window.onclick = function(event) {
            if (event.target == modal) {
                closeModal();
            }
        }
    }

    const schools = JSON.parse(document.getElementById('school-data').textContent);
    const searchInput = document.getElementById('schoolSearch');
    const dropdown = document.getElementById('schoolDropdown');
    const instituteCodeInput = document.getElementById('institute_code');
    
    function filterSchools(query) {
        if (!query) return [];
        const searchText = query.toLowerCase();
        return schools.filter(school => 
            school.search.includes(searchText)
        );
    }
    
    function updateDropdown(filtered) {
        dropdown.innerHTML = '';
        filtered.forEach(school => {
            const div = document.createElement('div');
            div.className = 'dropdown-item';
            div.innerHTML = `
                <div class="school-name">${school.name}</div>
                <div class="school-details">
                    <div class="school-code">Kód: ${school.code}</div>
                </div>
                <div class="school-location">
                    <div class="school-city">${school.city}</div>
                </div>
            `;
            div.onclick = () => {
                searchInput.value = school.name;
                instituteCodeInput.value = school.code;
                dropdown.style.display = 'none';
            };
            dropdown.appendChild(div);
        });
    }
    
    let debounceTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            const filtered = filterSchools(e.target.value);
            dropdown.style.display = filtered.length ? 'block' : 'none';
            updateDropdown(filtered);
        }, 150);
    });
    
    searchInput.addEventListener('focus', () => {
        if (searchInput.value) {
            const filtered = filterSchools(searchInput.value);
            dropdown.style.display = filtered.length ? 'block' : 'none';
            updateDropdown(filtered);
        }
    });
    
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
});

async function editTest(testId) {
    const modal = document.getElementById("editModal");
    const card = document.querySelector(`[data-test-id="${testId}"]`);
    const test = {
        subject: card.querySelector('h3').textContent,
        date: card.querySelector('.test-date').textContent,
        topic: card.querySelector('.test-topic').textContent,
        test_type: card.querySelector('.test-type').textContent.split('(')[0].trim(),
        weight: (card.querySelector('.test-type').textContent.match(/\((.*?)\)/) || [])[1],
        teacher: card.querySelector('.test-teacher').textContent
    };
    
    document.getElementById('edit_subject').value = test.subject;
    document.getElementById('edit_date').value = test.date;
    document.getElementById('edit_topic').value = test.topic;
    document.getElementById('edit_test_type').value = test.test_type;
    document.getElementById('edit_weight').value = test.weight || '';
    document.getElementById('edit_teacher').value = test.teacher;
    document.getElementById('edit_test_id').value = testId;
    
    modal.style.display = "block";
}

document.addEventListener('DOMContentLoaded', function() {
    const editForm = document.getElementById('editTestForm');
    if (editForm) {
        editForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const testId = document.getElementById('edit_test_id').value;
            const formData = {
                subject: document.getElementById('edit_subject').value,
                date: document.getElementById('edit_date').value,
                topic: document.getElementById('edit_topic').value,
                test_type: document.getElementById('edit_test_type').value,
                weight: document.getElementById('edit_weight').value || null,
                teacher: document.getElementById('edit_teacher').value || null
            };

            try {
                const response = await fetch(`/api/edit-test/${testId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                if (response.ok) {
                    window.location.reload();
                } else {
                    alert('Hiba történt a dolgozat szerkesztése közben!');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Hiba történt a dolgozat szerkesztése közben!');
            }
        });
    }
}); 