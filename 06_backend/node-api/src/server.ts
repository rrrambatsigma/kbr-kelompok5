
import "dotenv/config";
import app from "./app.js";

const PORT = Number(process.env.PORT) || 3000;

app.listen(PORT, () => {
  console.log("------------------------------------");
  console.log("KBR NODE API");
  console.log("------------------------------------");
  console.log(`Server running: http://localhost:${PORT}`);
  console.log(`Health check:   http://localhost:${PORT}/api/health`);
  console.log("------------------------------------");
});
