document.addEventListener('DOMContentLoaded', function() {
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