import React, { useState } from "react";
import UploadDI from "./components/UploadDI";
import DeliveryCalendar from "./components/DeliveryCalendar";
import MatrixTable from "./components/MatrixTable";

export default function App() {
  const [page, setPage] = useState("upload");

  return (
    <div>
      {/* 🔹 Simple Navigation Buttons */}
      <div className="d-flex justify-content-center gap-3 mt-4">
        <button
          className={`btn ${page === "upload" ? "btn-primary" : "btn-outline-primary"}`}
          onClick={() => setPage("upload")}
        >
          🗂 Upload Delivery Instruction
        </button>

        <button
          className={`btn ${page === "calendar" ? "btn-primary" : "btn-outline-primary"}`}
          onClick={() => setPage("calendar")}
        >
          📅 View Delivery Calendar
        </button>

        <button
          className={`btn ${page === "matrix" ? "btn-primary" : "btn-outline-primary"}`}
          onClick={() => setPage("matrix")}
        >
         *** MATRIX TABLE
        </button>
      </div>

      {/* 🔹 Render Components */}
      <div className="mt-4">
        {page === "upload" && <UploadDI />}
        {page === "calendar" && <DeliveryCalendar />}
        {page === "matrix" && <MatrixTable month={10} year={2025} version={1} />}
      </div>
    </div>
  );
}
