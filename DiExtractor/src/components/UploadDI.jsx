import React, { useState } from "react";
import axios from "axios";

export default function UploadDI() {
  const [file, setFile] = useState(null);
  const [factory, setFactory] = useState("F1");
  const [monthYear, setMonthYear] = useState("102025");
  const [bucket, setBucket] = useState("1");
  const [docVersion, setDocVersion] = useState("1");
  const [status, setStatus] = useState("");
  const [result, setResult] = useState(null);

  const handleUpload = async () => {
    if (!file) return alert("Please select a PDF file first.");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("factory", factory);
    formData.append("month_year", monthYear);
    formData.append("bucket", bucket);
    formData.append("version", docVersion);

    setStatus("⏳ Uploading & processing...");

    try {
      const res = await axios.post("http://localhost:8000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
      setStatus("✅ File processed successfully!");
    } catch (error) {
      console.error(error);
      setStatus("❌ Error processing file");
    }
  };

  return (
    <div className="container mt-5">
      <h4 className="mb-4">📄 Upload Purchase Schedule PDF</h4>

      <div className="row mb-3">
        <div className="col">
          <label>Factory</label>
          <input
            type="text"
            className="form-control"
            value={factory}
            onChange={(e) => setFactory(e.target.value)}
          />
        </div>
        <div className="col">
          <label>Month-Year (mmYYYY)</label>
          <input
            type="text"
            className="form-control"
            value={monthYear}
            onChange={(e) => setMonthYear(e.target.value)}
          />
        </div>
        <div className="col">
          <label>Bucket (0–4)</label>
          <input
            type="text"
            className="form-control"
            value={bucket}
            onChange={(e) => setBucket(e.target.value)}
          />
        </div>
        <div className="col">
          <label>Version (1–4)</label>
          <input
            type="text"
            className="form-control"
            value={docVersion}
            onChange={(e) => setDocVersion(e.target.value)}
          />
        </div>
      </div>

      <input
        type="file"
        accept=".pdf"
        className="form-control mb-3"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <button className="btn btn-primary" onClick={handleUpload}>
        Upload & Process
      </button>

      {status && <p className="mt-3">{status}</p>}

      {result && (
        <div className="mt-4">
          <h5>Extracted Header</h5>
          <pre>{JSON.stringify(result.extracted_header, null, 2)}</pre>
          <p>
            <strong>📂 Saved to:</strong> {result.saved_to}
          </p>
        </div>
      )}
    </div>
  );
}
