import React, { useEffect, useState } from "react";
import axios from "axios";

export default function MatrixTable() {
  const [month, setMonth] = useState(new Date().getMonth() + 1); // current month (1–12)
  const [year, setYear] = useState(new Date().getFullYear()); // current year
  const [version, setVersion] = useState(1);
  const [parts, setParts] = useState([]);
  const [days, setDays] = useState([]);
  const [selectedPart, setSelectedPart] = useState(null);

  // 🧮 Update number of days when month/year changes
  useEffect(() => {
    const numDays = new Date(year, month, 0).getDate();
    setDays(Array.from({ length: numDays }, (_, i) => i + 1));
  }, [month, year]);

  // 📡 Fetch data whenever month/year/version changes
  useEffect(() => {
    axios
      .get("http://localhost:8000/api/matrixtable", {
        params: { month, year, version },
      })
      .then((res) => {
        if (res.data.status === "success") {
          setParts(res.data.data);
          if (res.data.data.length > 0) {
            setSelectedPart(res.data.data[0]);
          }
        }
      })
      .catch((err) => console.error(err));
  }, [month, year, version]);

  return (
    <div className="container mt-4">
      <h4 className="mb-3 text-center">
        📦 Delivery Instruction Matrix
      </h4>

      {/* Month & Year Selectors */}
      <div className="d-flex justify-content-center align-items-center gap-3 mb-4">
        <div>
          <label className="form-label fw-bold mb-1">Month:</label>
          <select
            className="form-select"
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
          >
            {[
              "January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December",
            ].map((m, idx) => (
              <option key={idx + 1} value={idx + 1}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="form-label fw-bold mb-1">Year:</label>
          <select
            className="form-select"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i).map(
              (y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              )
            )}
          </select>
        </div>

        <div>
          <label className="form-label fw-bold mb-1">Version:</label>
          <select
            className="form-select"
            value={version}
            onChange={(e) => setVersion(Number(e.target.value))}
          >
            {[1, 2, 3, 4, 5].map((v) => (
              <option key={v} value={v}>
                v{v}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Part dropdown */}
      <div className="mb-3">
        <label className="form-label fw-bold">Select Part:</label>
        <select
          className="form-select"
          value={selectedPart?.part_number || ""}
          onChange={(e) => {
            const part = parts.find((p) => p.part_number === e.target.value);
            setSelectedPart(part);
          }}
        >
          {parts.map((p) => (
            <option key={p.part_number} value={p.part_number}>
              {p.part_number} — {p.part_desc}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      {selectedPart && (
        <div className="table-responsive">
          <h6 className="mb-2">
            🧩 <b>{selectedPart.part_number}</b> — {selectedPart.part_desc}
          </h6>
          <table className="table table-bordered table-sm text-center align-middle">
            <thead className="table-light">
              <tr>
                <th>Type</th>
                {days.map((d) => (
                  <th key={d}>{d}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="fw-bold">DI</td>
                {days.map((d) => (
                  <td
                    key={d}
                    className={
                      selectedPart.days[d] > 0
                        ? "bg-primary text-white fw-bold"
                        : "text-muted"
                    }
                  >
                    {selectedPart.days[d] || 0}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="fw-bold">Plan</td>
                {days.map((d) => (
                  <td key={d}>0</td>
                ))}
              </tr>
              <tr>
                <td className="fw-bold">Real</td>
                {days.map((d) => (
                  <td key={d}>0</td>
                ))}
              </tr>
              <tr>
                <td className="fw-bold">Delivery</td>
                {days.map((d) => (
                  <td key={d}>0</td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
