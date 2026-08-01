"use client";

import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { weatherApi } from "@/lib/api";
import { useLanguage } from "@/lib/i18n-context";
import { translateText } from "@/lib/client-translator";

const customMarkerIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface Coordinates {
  lat: number;
  lon: number;
  zoom: number;
}

function RecenterMap({ lat, lon, zoom }: { lat: number; lon: number; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lon], zoom);
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 150);
    return () => clearTimeout(timer);
  }, [lat, lon, zoom, map]);
  return null;
}

function cleanLocationQuery(rawLoc: string): string {
  if (!rawLoc) return "";
  return rawLoc
    .replace(/\s*[-–—|]\s*(reuters|ap|afp|bloomberg|cnn|bbc|press|news).*/i, "")
    .replace(/\([^)]*\)/g, "")
    .trim();
}

const Location = ({ location }: { location: string | null }) => {
  const { t, language } = useLanguage();
  const [coordinates, setCoordinates] = useState<Coordinates | null>(null);
  const [translatedLocationName, setTranslatedLocationName] = useState(location || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setCoordinates(null);
    setError("");
    if (!location) return;
    let isCancelled = false;

    const cleanedLocation = cleanLocationQuery(location);

    if (language === "en") {
      setTranslatedLocationName(cleanedLocation);
    } else {
      translateText(cleanedLocation, language).then((res) => {
        if (!isCancelled) setTranslatedLocationName(res);
      });
    }

    const cacheKey = `v3_coords_${cleanedLocation.toLowerCase().replace(/\s+/g, "_")}`;
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
        let coords: Coordinates | null = null;

        // 1. OpenStreetMap Nominatim Geocoding (Primary - supports Countries, Regions, Cities & Places accurately)
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(cleanedLocation)}&limit=1`,
            { headers: { "Accept-Language": "en" } }
          );
          if (res.ok) {
            const data = await res.json();
            if (Array.isArray(data) && data.length > 0 && data[0].lat && data[0].lon) {
              const placeType = String(data[0].type || data[0].addresstype || "").toLowerCase();
              const placeClass = String(data[0].class || "").toLowerCase();
              const isCountry = placeType === "country" || placeClass === "boundary" || !cleanedLocation.includes(",");
              const zoom = isCountry ? 4 : 11;

              coords = { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon), zoom };
            }
          }
        } catch {
          // Fall through to backend geocode if network error
        }

        // 2. Backend OpenWeather geocoding fallback
        if (!coords) {
          try {
            const response = await weatherApi.geocode(cleanedLocation);
            if (Array.isArray(response) && response.length > 0 && response[0].lat && response[0].lon) {
              coords = { lat: Number(response[0].lat), lon: Number(response[0].lon), zoom: 10 };
            }
          } catch {
            // ignore
          }
        }

        if (coords && !isCancelled) {
          try {
            localStorage.setItem(cacheKey, JSON.stringify(coords));
          } catch {
            // ignore storage quota errors
          }
          setCoordinates(coords);
        } else if (!isCancelled) {
          setError("Location coordinates not found.");
          setCoordinates(null);
        }
      } catch (err) {
        if (!isCancelled) {
          setError("Failed to fetch location.");
          setCoordinates(null);
        }
      } finally {
        if (!isCancelled) setLoading(false);
      }
    };

    fetchCoordinates();

    return () => {
      isCancelled = true;
    };
  }, [location, language]);

  if (!location) return null;

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <h2 className="text-xl sm:text-2xl font-bold mb-4">{t("location_map")}: {translatedLocationName}</h2>

      {loading && <p className="text-sm text-muted-foreground">Loading map for {translatedLocationName}...</p>}
      {error && <p className="text-red-500 text-sm">{error}</p>}

      {coordinates ? (
        <div className="mt-4 h-64 sm:h-80 rounded-2xl overflow-hidden border relative z-0">
          <MapContainer
            key={`${coordinates.lat}-${coordinates.lon}-${coordinates.zoom}`}
            center={[coordinates.lat, coordinates.lon]}
            zoom={coordinates.zoom}
            scrollWheelZoom={false}
            style={{ height: "100%", width: "100%" }}
          >
            <RecenterMap lat={coordinates.lat} lon={coordinates.lon} zoom={coordinates.zoom} />
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="© OpenStreetMap contributors"
            />
            <Marker position={[coordinates.lat, coordinates.lon]} icon={customMarkerIcon}>
              <Popup>
                <div className="font-semibold text-sm">{translatedLocationName}</div>
              </Popup>
            </Marker>
          </MapContainer>
        </div>
      ) : (
        !loading &&
        !error && (
          <p className="text-muted-foreground text-sm">
            {t("no_coordinates")}
          </p>
        )
      )}
    </div>
  );
};

export default Location;
