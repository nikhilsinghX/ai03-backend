import { api } from "./api.js";

document.getElementById("testApi").onclick = async () => {
  const out = document.getElementById("result");
  try {
    out.textContent = JSON.stringify(await api.health(), null, 2);
  } catch (e) {
    out.textContent = "Error: " + e.message;
  }
};