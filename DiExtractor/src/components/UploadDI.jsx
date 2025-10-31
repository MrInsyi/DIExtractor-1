import React, { useState } from "react";
import axios from "axios";

export default function UploadDI() {
  const [file, setFile] = useState(null);
  const [factory, setFactory] = useState("F1");
  const [monthYear, setMonthYear] = useState("102025");
  const [bucket, setBucket] = useState("1");
  const [docVersion, setDocVersion] = useState("1");
  const [mode, setMode] = useState("Manual"); // 👈 OCR or Manual
  const [status, setStatus] = useState("");
  const [result, setResult] = useState(null);

  // Manual data input (header)
  const [manualData, setManualData] = useState({
    purchaseSchedule: "",
    customerName: "",
    customerCode: "",
    partNumber: "",
    partDesc: "",
  });

  // Quantity data (date → qty)
  const [quantities, setQuantities] = useState([{ date: "", qty: "" }]);

  // Upload handler
  const handleUpload = async () => {
    if (mode === "OCR" && !file) return alert("Please select a PDF file first.");

    const formData = new FormData();
    formData.append("factory", factory);
    formData.append("month_year", monthYear);
    formData.append("bucket", bucket);
    formData.append("version", docVersion);

    if (mode === "OCR") {
      formData.append("file", file);
    } else {
      formData.append("manual_data", JSON.stringify(manualData));
      formData.append("quantities", JSON.stringify(quantities));
    }

    setStatus("⏳ Uploading & processing...");

    try {
      const url =
        mode === "OCR"
          ? "http://localhost:8000/upload"
          : "http://localhost:8000/manual_upload";

      const res = await axios.post(url, formData, {
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
      <h4 className="mb-4">📄 Upload or Input Delivery Instruction</h4>

      {/* Mode Switch */}
      <div className="mb-3">
        <label className="form-label me-3">Mode:</label>
        <div className="form-check form-check-inline">
          <input
            className="form-check-input"
            type="radio"
            name="mode"
            value="OCR"
            checked={mode === "OCR"}
            onChange={() => setMode("OCR")}
          />
          <label className="form-check-label">OCR Mode</label>
        </div>
        <div className="form-check form-check-inline">
          <input
            className="form-check-input"
            type="radio"
            name="mode"
            value="Manual"
            checked={mode === "Manual"}
            onChange={() => setMode("Manual")}
          />
          <label className="form-check-label">Manual Input</label>
        </div>
      </div>

      {/* Common Info */}
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

      {/* OCR Mode */}
      {mode === "OCR" && (
        <div>
          <input
            type="file"
            accept=".pdf"
            className="form-control mb-3"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </div>
      )}

      {/* Manual Mode */}
      {mode === "Manual" && (
        <div className="card p-3 mb-3">
          <h6>📝 Manual Input</h6>

          {/* Header Fields */}
          {Object.entries(manualData).map(([key, value]) => (
            <div className="mb-2" key={key}>
              <label className="form-label text-capitalize">
                {key.replace(/([A-Z])/g, " $1")}
              </label>
              <input
                type="text"
                className="form-control"
                value={value}
                onChange={(e) =>
                  setManualData({ ...manualData, [key]: e.target.value })
                }
              />
            </div>
          ))}

          {/* 📅 Quantity Section */}
          <div className="mt-4">
            <h6>📅 Quantity by Date</h6>
            {quantities.map((q, index) => (
              <div className="row mb-2" key={index}>
                <div className="col">
                  <input
                    type="date"
                    className="form-control"
                    value={q.date}
                    onChange={(e) => {
                      const newQ = [...quantities];
                      newQ[index].date = e.target.value;
                      setQuantities(newQ);
                    }}
                  />
                </div>
                <div className="col">
                  <input
                    type="number"
                    className="form-control"
                    placeholder="Quantity"
                    value={q.qty}
                    onChange={(e) => {
                      const newQ = [...quantities];
                      newQ[index].qty = e.target.value;
                      setQuantities(newQ);
                    }}
                  />
                </div>
                <div className="col-auto">
                  <button
                    className="btn btn-danger"
                    type="button"
                    onClick={() =>
                      setQuantities(quantities.filter((_, i) => i !== index))
                    }
                  >
                    🗑
                  </button>
                </div>
              </div>
            ))}

            <button
              className="btn btn-outline-success"
              type="button"
              onClick={() =>
                setQuantities([...quantities, { date: "", qty: "" }])
              }
            >
              ➕ Add Row
            </button>
          </div>
        </div>
      )}

      {/* Upload / Save Button */}
      <button className="btn btn-primary" onClick={handleUpload}>
        {mode === "OCR" ? "Upload & Process" : "Save Manual Entry"}
      </button>

      {status && <p className="mt-3">{status}</p>}

      {/* Result Section */}
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
