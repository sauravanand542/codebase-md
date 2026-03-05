import React from "react";
import { greet } from "@my/core";

export default function App() {
  return (
    <div>
      <h1>{greet("World")}</h1>
    </div>
  );
}
