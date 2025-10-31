import React, { useEffect, useState } from "react";
import axios from "axios";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";

export default function DeliveryCalendar() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [month, setMonth] = useState("10");
  const [year, setYear] = useState("2025");
  const [version, setVersion] = useState("1");

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(
        `http://localhost:8000/api/delivery-calendar?month=${month}&year=${year}&version=${version}`
      );
      if (res.data.status === "success") {
        const formatted = res.data.data.map((item) => ({
          title: `${item.total_parts} parts • ${item.total_qty} pcs`,
          date: item.date,
        }));
        setEvents(formatted);
      }
    } catch (err) {
      console.error("❌ Error fetching calendar data:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, [month, year, version]);

  return (
    <div className="container mt-5">
      <h4 className="mb-3 text-center">📅 Delivery Instruction Calendar</h4>

      {/* Filters */}
      <div className="d-flex justify-content-center gap-3 mb-3">
        <input
          type="text"
          className="form-control w-auto"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          placeholder="Month (e.g. 10)"
        />
        <input
          type="text"
          className="form-control w-auto"
          value={year}
          onChange={(e) => setYear(e.target.value)}
          placeholder="Year (e.g. 2025)"
        />
        <input
          type="text"
          className="form-control w-auto"
          value={version}
          onChange={(e) => setVersion(e.target.value)}
          placeholder="Version"
        />
        <button className="btn btn-primary" onClick={loadData}>
          🔄 Refresh
        </button>
      </div>

      {/* Calendar */}
      {loading ? (
        <p className="text-center">⏳ Loading...</p>
      ) : (
        <FullCalendar
          plugins={[dayGridPlugin]}
          initialView="dayGridMonth"
          events={events}
          height="auto"
        />
      )}
    </div>
  );
}
