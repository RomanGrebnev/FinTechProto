import { useEffect, useState } from "react";
import { api } from "./api";

// Latest stored AI analysis, plus a function to generate a fresh one
export default function useAnalysis() {
  const [analysis, setAnalysis] = useState(undefined); // undefined = loading, null = none yet
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/recommendations/latest").then(setAnalysis).catch((e) => { setError(e.message); setAnalysis(null); });
  }, []);

  const generate = async () => {
    setGenerating(true);
    setError("");
    try {
      setAnalysis(await api("/recommendations", { method: "POST" }));
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  return { analysis, generating, error, generate };
}
