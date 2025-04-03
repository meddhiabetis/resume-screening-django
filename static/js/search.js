document.getElementById('searchForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    fetch('/resume/search/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the UI with search results
            const resultsDiv = document.getElementById('searchResults');
            resultsDiv.innerHTML = '';
            
            data.results.forEach(result => {
                resultsDiv.innerHTML += `
                    <div class="search-result">
                        <h4>Resume ID: ${result.resume_id}</h4>
                        <p>Score: ${result.score}</p>
                        <p>Content: ${result.content}</p>
                        <p>Section: ${result.section_type}</p>
                    </div>
                `;
            });
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while searching');
    });
});

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}