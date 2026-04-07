// Auto-dismiss flash alerts after 4 seconds
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity .5s';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 500);
    }, 4000);
  });
});

// Live book search via API (debounced)
const searchInput = document.querySelector('.search-input');
if (searchInput && window.location.pathname.includes('/student/search')) {
  let timeout;
  searchInput.addEventListener('input', () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      searchInput.closest('form').submit();
    }, 500);
  });
}
