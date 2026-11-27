import { useEffect, useState } from "react";
import { errorMessage, getText } from "./api";

export function Instructions() {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getText("/api/agent/instructions")
      .then(setText)
      .catch((failure: unknown) => {
        setError(errorMessage(failure));
      });
  }, []);

  return (
    <section className="panel">
      <h1>Agent instructions</h1>
      <p className="muted">These are read only.</p>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      {text !== null && <pre className="instructions">{text}</pre>}
    </section>
  );
}
