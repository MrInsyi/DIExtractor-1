import React, { useEffect, useState } from "react";
import axios from "axios";

export default function MatrixTable({ month, year, version }) {
  const [parts, setParts] = useState([]);
  const [days, setDays] = useState([]);
  const [selectedPart, setSelectedPart] = useState(null);

  useEffect(() => {
    const numDays = new Date(year, month, 0).getDate();
    setDays(Array.from({ length: numDays }, (_, i) => i + 1));

    axios
      .get("http://localhost:8000/api/matrixtable", {
        params: { month, year, version },
      })
      .then((res) => {
        if (res.data.status === "success") {
          setParts(res.data.data);
          if (res.data.data.length > 0) {
            setSelectedPart(res.data.data[0]); // auto-select first
          }
        }
      })
      .catch((err) => console.error(err));
  }, [month, year, version]);

  return (
    <div className="container mt-4">
      <h4 className="mb-3 text-center">
        📦 Delivery Instruction Matrix – {month}/{year}
      </h4>

      {/* Dropdown to select part */}
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
              {/* DI row */}
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

              {/* Future rows */}
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
