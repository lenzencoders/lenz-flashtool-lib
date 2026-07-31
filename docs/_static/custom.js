(function () {
    function bindBackToTop() {
        var btn = document.getElementById('pst-back-to-top');
        if (!btn) return;
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindBackToTop);
    } else {
        bindBackToTop();
    }
})();
