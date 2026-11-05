document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('form[action*="/transactions/"]').forEach(form => {
    form.addEventListener("submit", event => {
      const amount = form.querySelector('input[name="amount"]');
      if (amount && (!amount.value || Number(amount.value) <= 0)) {
        event.preventDefault();
        amount.focus();
        alert("Please enter an amount greater than zero.");
      }
    });
  });
});
