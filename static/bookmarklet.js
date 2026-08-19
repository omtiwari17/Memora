(function () {
    var text = window.getSelection().toString().trim();
    if (!text) {
        alert('Select some text on the page first, then click the bookmarklet.');
        return;
    }
    var author = prompt('Author (optional):', '') || '';
    fetch('https://YOUR-DOMAIN.onrender.com/api/capture/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            author: author,
            source_url: window.location.href,
            source_title: document.title
        })
    })
        .then(function (r) { return r.ok ? alert('Saved to Memora ✓') : alert('Failed to save.'); })
        .catch(function (e) { alert('Error: ' + e); });
})();
