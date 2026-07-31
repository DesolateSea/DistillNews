"use client";

import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { weatherApi } from "@/lib/api";

// Fix for default marker icons not showing
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require("leaflet/dist/images/marker-icon-2x.png").default,
  iconUrl: require("leaflet/dist/images/marker-icon.png").default,
  shadowUrl: require("leaflet/dist/images/marker-shadow.png").default,
});

interface Coordinates {
  lat: number;
  lon: number;
}

const Location = ({ location }: { location: string | null }) => {
  const [coordinates, setCoordinates] = useState<Coordinates | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!location) return;

    const cacheKey = `coords_${location.toLowerCase().replace(/\s+/g, "_")}`;
    const cached = localStorage.getItem(cacheKey);

    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (parsed.lat && parsed.lon) {
          setCoordinates(parsed);
          return;
        }
      } catch {
        localStorage.removeItem(cacheKey); // Corrupt cache cleanup
      }
    }

    const fetchCoordinates = async () => {
      setLoading(true);
      setError("");

      try {
        const response = await weatherApi.geocode(location);

        if (response.length === 0) {
          setError("Location not found.");
          setCoordinates(null);
        } else {
          const { lat, lon } = response[0];
          const coords = { lat, lon };
          localStorage.setItem(cacheKey, JSON.stringify(coords));
          setCoordinates(coords);
        }
      } catch (err) {
        setError("Failed to fetch location.");
        setCoordinates(null);
        localStorage.removeItem(cacheKey);
      } finally {
        setLoading(false);
      }
    };

    fetchCoordinates();
  }, [location]);

  if (!location) return null;

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h2 className="text-2xl font-semibold mb-4">Location: {location}</h2>

      {loading && <p>Loading map for {location}...</p>}
      {error && <p className="text-red-500">{error}</p>}

      {coordinates ? (
        <div className="mt-4 h-64">
          <MapContainer
            center={[coordinates.lat, coordinates.lon]}
            zoom={13}
            scrollWheelZoom={false}
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="© OpenStreetMap contributors"
            />
            <Marker position={[coordinates.lat, coordinates.lon]}>
              <Popup>
                {location} <br />
                Lat: {coordinates.lat}, Lon: {coordinates.lon}
              </Popup>
            </Marker>
          </MapContainer>
        </div>
      ) : (
        !loading &&
        !error && (
          <p className="text-muted-foreground">
            No coordinates available for this location.
          </p>
        )
      )}
    </div>
  );
};

export default Location;
