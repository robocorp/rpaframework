function resizeFrames() {
  var iframes = document.querySelectorAll("iframe");
  for (var i = 0; i < iframes.length; i++) {
    height = iframes[i].contentWindow.document.body.scrollHeight + 80;
    iframes[i].style.height = height + "px";
  }
}

window.addEventListener("DOMContentLoaded", function (e) {
  setInterval(resizeFrames, 1000);
});
