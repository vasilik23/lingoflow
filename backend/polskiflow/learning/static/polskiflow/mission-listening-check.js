const listeningCheck = document.querySelector('[data-listening-check]');
if (listeningCheck) {
  const result = listeningCheck.querySelector('[data-listening-result]');
  listeningCheck.addEventListener('click', event => {
    const choice = event.target.closest('[data-listening-choice]');
    if (choice) {
      result.textContent = listeningCheck.dataset[choice.dataset.listeningChoice];
    }
  });
  listeningCheck.hidden = false;
}
