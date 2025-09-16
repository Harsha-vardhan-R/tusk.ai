(function() {
    const params = new URLSearchParams(window.location.search);
    const data = params.get('data') || '';
    document.body.textContent = data;
})();
