import React, { useEffect, useState } from "react";
import axios from "axios";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";

export default function DeliveryCalendar() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    axios
      .get("http://localhost:8000/api/delivery-calendar?month=10&year=2025&version=1")
      .then((res) => {
        if (res.data.status === "success") {
          const formatted = res.data.data.map((item) => ({
            title: `${item.total_parts} parts • ${item.total_qty} pcs`,
            date: item.date,
          }));
          setEvents(formatted);
        }
      })
      .catch((err) => console.error("Error loading calendar:", err));
  }, []);

  return (
    <div className="container mt-4">
      <h4 className="mb-3 text-center">📅 Delivery Instruction Calendar</h4>
      <FullCalendar
        plugins={[dayGridPlugin]}
        initialView="dayGridMonth"
        events={events}
        height="auto"
      />
    </div>
  );
}
