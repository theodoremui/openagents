/**
 * Interactive Map Component
 *
 * Renders interactive Google Maps using @vis.gl/react-google-maps library.
 * Supports three map types:
 * 1. Route maps with directions
 * 2. Location maps centered on a point
 * 3. Places maps with multiple markers
 *
 * This component is rendered when the chat interface detects a JSON code block
 * with type: "interactive_map" from the MapAgent's response.
 */

'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { APIProvider, Map, AdvancedMarker, useMap, useMapsLibrary, Pin } from '@vis.gl/react-google-maps';
import { Loader2, AlertCircle } from 'lucide-react';

/**
 * Configuration for interactive map
 */
interface InteractiveMapConfig {
  map_type: 'route' | 'location' | 'places';
  origin?: string;
  destination?: string;
  waypoints?: string[];
  center?: { lat: number; lng: number };
  zoom?: number;
  markers?: Array<{
    lat?: number;
    lng?: number;
    address?: string;
    title?: string;
    type?: string;
  }>;
  travel_mode?: 'DRIVING' | 'WALKING' | 'BICYCLING' | 'TRANSIT';
}

interface InteractiveMapProps {
  config: InteractiveMapConfig;
}

/**
 * Places Auto-Fit Component
 * Automatically adjusts map bounds to fit all markers
 */
function PlacesAutoBounds({ markers }: { markers: Array<{ lat: number; lng: number }> }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !markers || markers.length === 0) return;

    // Create bounds object
    const bounds = new google.maps.LatLngBounds();

    // Extend bounds to include all markers
    markers.forEach(marker => {
      bounds.extend({ lat: marker.lat, lng: marker.lng });
    });

    // Fit map to bounds with padding
    map.fitBounds(bounds, {
      top: 50,
      right: 50,
      bottom: 50,
      left: 50
    });
  }, [map, markers]);

  return null;
}

/**
 * Directions Component
 * Handles route rendering using Google Maps Directions API
 */
function Directions({ config }: { config: InteractiveMapConfig }) {
  const map = useMap();
  const routesLibrary = useMapsLibrary('routes');
  const [directionsService, setDirectionsService] = useState<google.maps.DirectionsService>();
  const [directionsRenderer, setDirectionsRenderer] = useState<google.maps.DirectionsRenderer>();
  const [routes, setRoutes] = useState<google.maps.DirectionsRoute[]>([]);
  const [routeIndex, setRouteIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Initialize directions service and renderer
  useEffect(() => {
    if (!routesLibrary || !map) return;

    setDirectionsService(new routesLibrary.DirectionsService());
    setDirectionsRenderer(new routesLibrary.DirectionsRenderer({
      map,
      suppressMarkers: false,
      polylineOptions: {
        strokeColor: '#4285F4',
        strokeWeight: 5,
        strokeOpacity: 0.8
      }
    }));
  }, [routesLibrary, map]);

  // Fetch and render directions
  useEffect(() => {
    if (!directionsService || !directionsRenderer || !config.origin || !config.destination) return;

    const request: google.maps.DirectionsRequest = {
      origin: config.origin,
      destination: config.destination,
      travelMode: google.maps.TravelMode[config.travel_mode || 'DRIVING'],
      provideRouteAlternatives: false,
      waypoints: config.waypoints?.map(location => ({
        location,
        stopover: true
      })) || []
    };

    directionsService
      .route(request)
      .then(response => {
        directionsRenderer.setDirections(response);
        setRoutes(response.routes);
        setError(null);

        // Auto-fit bounds to show entire route
        if (response.routes[0]?.bounds && map) {
          map.fitBounds(response.routes[0].bounds);
        }
      })
      .catch(err => {
        console.error('Directions request failed:', err);
        setError('Failed to load directions. Please check the addresses and try again.');
      });
  }, [directionsService, directionsRenderer, config, map]);

  // Update route when index changes
  useEffect(() => {
    if (!directionsRenderer) return;
    directionsRenderer.setRouteIndex(routeIndex);
  }, [routeIndex, directionsRenderer]);

  if (error) {
    return (
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-destructive/90 text-destructive-foreground px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 z-10">
        <AlertCircle className="h-4 w-4" />
        <span className="text-sm">{error}</span>
      </div>
    );
  }

  if (routes.length > 0 && routes[routeIndex]) {
    const route = routes[routeIndex];
    const leg = route.legs[0];

    return (
      <div className="absolute bottom-4 left-4 bg-background/95 backdrop-blur-sm p-3 rounded-lg shadow-xl border border-border/50 max-w-xs z-10">
        <div className="text-sm font-semibold mb-1">Route Information</div>
        <div className="text-xs text-muted-foreground space-y-1">
          <div>Distance: <span className="font-medium">{leg.distance?.text}</span></div>
          <div>Duration: <span className="font-medium">{leg.duration?.text}</span></div>
          {config.travel_mode && config.travel_mode !== 'DRIVING' && (
            <div>Mode: <span className="font-medium capitalize">{config.travel_mode.toLowerCase()}</span></div>
          )}
        </div>
      </div>
    );
  }

  return null;
}

/**
 * Main Interactive Map Component
 */
export function InteractiveMap({ config }: InteractiveMapProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolvedMarkers, setResolvedMarkers] = useState<Array<{ lat: number; lng: number; title?: string; type?: string }> | null>(null);

  // Get API key from environment
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

  // Validate API key
  useEffect(() => {
    if (!apiKey) {
      setError('Google Maps API key is not configured. Please add NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to your .env.local file.');
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, [apiKey]);

  // Resolve address-only markers to lat/lng using browser-side Geocoder (uses the JS API key).
  useEffect(() => {
    if (!apiKey) return;
    if (config.map_type === 'route') {
      setResolvedMarkers(null);
      return;
    }
    const markers = config.markers || [];
    if (markers.length === 0) {
      setResolvedMarkers(null);
      return;
    }

    const needsGeocoding = markers.some((m) => (typeof m.lat !== 'number' || typeof m.lng !== 'number') && typeof m.address === 'string' && m.address.trim());
    if (!needsGeocoding) {
      // Normalize to the concrete type we render with (lat/lng guaranteed).
      const concrete = markers
        .filter((m): m is { lat: number; lng: number; title?: string; type?: string } => typeof m.lat === 'number' && typeof m.lng === 'number')
        .map((m) => ({ lat: m.lat, lng: m.lng, title: m.title, type: m.type }));
      setResolvedMarkers(concrete);
      return;
    }

    // Guard: google may not be present until Maps JS is loaded; fail safe without crashing.
    if (typeof window === 'undefined' || typeof google === 'undefined' || !google.maps || !(google.maps as any).Geocoder) {
      setResolvedMarkers(
        markers
          .filter((m): m is { lat: number; lng: number; title?: string; type?: string } => typeof m.lat === 'number' && typeof m.lng === 'number')
          .map((m) => ({ lat: m.lat, lng: m.lng, title: m.title, type: m.type }))
      );
      return;
    }

    let cancelled = false;
    const geocoder = new (google.maps as any).Geocoder();

    const geocodeOne = (address: string) =>
      new Promise<{ lat: number; lng: number } | null>((resolve) => {
        geocoder.geocode({ address }, (results: any[], status: string) => {
          try {
            if (status !== 'OK' || !results || results.length === 0) return resolve(null);
            const loc = results[0]?.geometry?.location;
            const lat = typeof loc?.lat === 'function' ? loc.lat() : loc?.lat;
            const lng = typeof loc?.lng === 'function' ? loc.lng() : loc?.lng;
            if (typeof lat === 'number' && typeof lng === 'number') return resolve({ lat, lng });
            return resolve(null);
          } catch {
            return resolve(null);
          }
        });
      });

    (async () => {
      const out: Array<{ lat: number; lng: number; title?: string; type?: string }> = [];
      for (const m of markers) {
        if (typeof m.lat === 'number' && typeof m.lng === 'number') {
          out.push({ lat: m.lat, lng: m.lng, title: m.title, type: m.type });
          continue;
        }
        const addr = (m.address || '').trim();
        if (!addr) continue;
        const coords = await geocodeOne(addr);
        if (coords) out.push({ ...coords, title: m.title, type: m.type });
      }
      if (!cancelled) {
        setResolvedMarkers(out);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [apiKey, config]);

  // Calculate initial center and zoom
  const getInitialCenter = () => {
    if (config.center) {
      return config.center;
    }

    const ms = resolvedMarkers ?? (config.markers || []).filter((m): m is { lat: number; lng: number } => typeof m.lat === 'number' && typeof m.lng === 'number');
    if (ms.length > 0) {
      const center_lat = ms.reduce((s, m) => s + m.lat, 0) / ms.length;
      const center_lng = ms.reduce((s, m) => s + m.lng, 0) / ms.length;
      return { lat: center_lat, lng: center_lng };
    }

    // Default to San Francisco if no center provided
    return { lat: 37.7749, lng: -122.4194 };
  };

  const getInitialZoom = () => {
    if (config.zoom !== undefined) {
      return config.zoom;
    }

    // Default zoom based on map type
    switch (config.map_type) {
      case 'route':
        return 10; // Wider view for routes
      case 'location':
        return 14; // Closer view for single location
      case 'places':
        return (resolvedMarkers ?? config.markers)?.length === 1 ? 15 : 13; // Zoom in for single place
      default:
        return 12;
    }
  };

  // Error state
  if (error) {
    return (
      <div className="w-full h-[500px] rounded-lg overflow-hidden shadow-xl my-4 border border-destructive/30 bg-destructive/5 flex items-center justify-center">
        <div className="text-center p-8 max-w-md">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Map Error</h3>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="w-full h-[500px] rounded-lg overflow-hidden shadow-xl my-4 border border-border/30 bg-muted/20 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">Loading map...</p>
        </div>
      </div>
    );
  }

  if (!apiKey) {
    return null; // Error already shown
  }

  return (
    <div className="w-full h-[500px] rounded-lg overflow-hidden shadow-xl my-4 border border-border/30 relative">
      <APIProvider apiKey={apiKey}>
        <Map
          defaultCenter={getInitialCenter()}
          defaultZoom={getInitialZoom()}
          gestureHandling="greedy"
          disableDefaultUI={false}
          mapId={process.env.NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID || 'openagents-map'}
          className="w-full h-full"
          style={{ width: '100%', height: '100%' }}
        >
          {/* Render route with directions */}
          {config.map_type === 'route' && config.origin && config.destination && (
            <Directions config={config} />
          )}

          {/* Auto-fit bounds for places maps with multiple markers */}
          {config.map_type === 'places' && (resolvedMarkers ?? config.markers) && (resolvedMarkers ?? config.markers)!.length > 1 && (
            <PlacesAutoBounds markers={(resolvedMarkers ?? config.markers) as Array<{ lat: number; lng: number }>} />
          )}

          {/* Render markers for location/places maps with visible labels */}
          {config.map_type !== 'route' && (resolvedMarkers ?? config.markers) && (resolvedMarkers ?? config.markers)!.length > 0 && (
            <>
              {(resolvedMarkers ?? (config.markers as any)).map((marker: any, idx: number) => (
                <AdvancedMarker
                  key={idx}
                  position={{ lat: marker.lat, lng: marker.lng }}
                  title={marker.title || `Location ${idx + 1}`}
                >
                  {/* Custom marker with visible label */}
                  <div className="flex flex-col items-center">
                    {/* Pin */}
                    <div className="relative">
                      <Pin
                        background="#EA4335"
                        borderColor="#B00020"
                        glyphColor="#FFFFFF"
                      />
                    </div>
                    {/* Label below pin */}
                    {marker.title && (
                      <div className="mt-1 bg-white/95 backdrop-blur-sm px-2 py-1 rounded shadow-lg border border-gray-200 text-xs font-medium text-gray-900 whitespace-nowrap max-w-[200px] truncate">
                        {marker.title}
                      </div>
                    )}
                  </div>
                </AdvancedMarker>
              ))}
            </>
          )}

          {/* Render single marker for location map if no markers provided */}
          {config.map_type === 'location' && (!config.markers || config.markers.length === 0) && config.center && (
            <AdvancedMarker
              position={config.center}
              title="Location"
            >
              <div className="flex flex-col items-center">
                <div className="relative">
                  <Pin
                    background="#4285F4"
                    borderColor="#1967D2"
                    glyphColor="#FFFFFF"
                  />
                </div>
                <div className="mt-1 bg-white/95 backdrop-blur-sm px-2 py-1 rounded shadow-lg border border-gray-200 text-xs font-medium text-gray-900 whitespace-nowrap">
                  Location
                </div>
              </div>
            </AdvancedMarker>
          )}
        </Map>
      </APIProvider>

      {/* Map type indicator */}
      <div className="absolute top-4 right-4 bg-background/95 backdrop-blur-sm px-3 py-1 rounded-full shadow-lg border border-border/50 text-xs font-medium z-10">
        {config.map_type === 'route' && '🗺️ Route Map'}
        {config.map_type === 'location' && '📍 Location Map'}
        {config.map_type === 'places' && '📌 Places Map'}
      </div>
    </div>
  );
}
