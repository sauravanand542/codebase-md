import React, { useEffect, useState } from "react";
import axios from "axios";

export default function App() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    axios.get("/api/status").then((res) => setStatus(res.data));
  }, []);

  return (
    <div>
      <h1>Mixed Project</h1>
      <p>Server status: {status ? status.status : "loading..."}</p>
    </div>
  );
}
