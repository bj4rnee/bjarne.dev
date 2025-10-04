const copyBtn = document.getElementById("copy_btn");
if (copyBtn) {
  copyBtn.addEventListener("click", function () {
    const input = document.getElementById("short_hash");
    const icon = document.getElementById("copy_icon");

    input.select();
    input.setSelectionRange(0, 99999); // select text for mobile devices

    navigator.clipboard.writeText(input.value)
      .then(() => {
        // change icon to checkmark
        icon.classList.remove("fa-copy", "fa-solid");
        icon.classList.add("fa-check", "fa-solid");

        // revert after 2 seconds
        setTimeout(() => {
          icon.classList.remove("fa-check", "fa-solid");
          icon.classList.add("fa-copy", "fa-solid");
        }, 2000);
      })
      .catch(err => {
        console.error("[Error]: copy failed.", err);
      });
  });
}