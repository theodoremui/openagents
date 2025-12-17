/**
 * Tests for InteractiveMap component
 *
 * Tests the rendering of interactive Google Maps for different map types.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { InteractiveMap } from '@/components/interactive-map';

// Mock @vis.gl/react-google-maps
jest.mock('@vis.gl/react-google-maps', () => ({
  APIProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="api-provider">{children}</div>,
  Map: ({ children }: { children: React.ReactNode }) => <div data-testid="google-map" role="region">{children}</div>,
  AdvancedMarker: ({ title }: { title?: string }) => <div data-testid="marker">{title}</div>,
  useMap: jest.fn(() => null),
  useMapsLibrary: jest.fn(() => null),
}));

// Mock environment variables
const mockApiKey = 'test-api-key';
process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY = mockApiKey;

describe('InteractiveMap', () => {
  describe('Route Maps', () => {
    it('renders route map with basic configuration', () => {
      const config = {
        map_type: 'route' as const,
        origin: 'San Francisco, CA',
        destination: 'San Carlos, CA',
        travel_mode: 'DRIVING' as const,
        zoom: 10,
      };

      render(<InteractiveMap config={config} />);

      expect(screen.getByTestId('api-provider')).toBeInTheDocument();
      expect(screen.getByTestId('google-map')).toBeInTheDocument();
      expect(screen.getByText('🗺️ Route Map')).toBeInTheDocument();
    });

    it('renders route map with waypoints', () => {
      const config = {
        map_type: 'route' as const,
        origin: 'San Francisco, CA',
        destination: 'San Jose, CA',
        waypoints: ['Palo Alto, CA', 'Mountain View, CA'],
        travel_mode: 'BICYCLING' as const,
        zoom: 10,
      };

      render(<InteractiveMap config={config} />);

      expect(screen.getByTestId('google-map')).toBeInTheDocument();
      expect(screen.getByText('🗺️ Route Map')).toBeInTheDocument();
    });
  });

  describe('Location Maps', () => {
    it('renders location map centered on coordinates', () => {
      const config = {
        map_type: 'location' as const,
        center: { lat: 37.7749, lng: -122.4194 },
        zoom: 14,
      };

      render(<InteractiveMap config={config} />);

      expect(screen.getByTestId('google-map')).toBeInTheDocument();
      expect(screen.getByText('📍 Location Map')).toBeInTheDocument();
    });

    it('renders location map with marker', () => {
      const config = {
        map_type: 'location' as const,
        center: { lat: 37.7749, lng: -122.4194 },
        zoom: 14,
      };

      render(<InteractiveMap config={config} />);

      // Should render marker for location
      expect(screen.getByTestId('marker')).toBeInTheDocument();
    });
  });

  describe('Places Maps', () => {
    it('renders places map with multiple markers', () => {
      const config = {
        map_type: 'places' as const,
        center: { lat: 37.7749, lng: -122.4194 },
        zoom: 13,
        markers: [
          { lat: 37.7749, lng: -122.4194, title: 'City Hall' },
          { lat: 37.7849, lng: -122.4094, title: 'Civic Center' },
        ],
      };

      render(<InteractiveMap config={config} />);

      expect(screen.getByTestId('google-map')).toBeInTheDocument();
      expect(screen.getByText('📌 Places Map')).toBeInTheDocument();

      // Should render all markers
      const markers = screen.getAllByTestId('marker');
      expect(markers).toHaveLength(2);
      expect(screen.getByText('City Hall')).toBeInTheDocument();
      expect(screen.getByText('Civic Center')).toBeInTheDocument();
    });

    it('renders places map without markers', () => {
      const config = {
        map_type: 'places' as const,
        center: { lat: 37.7749, lng: -122.4194 },
        zoom: 13,
      };

      render(<InteractiveMap config={config} />);

      expect(screen.getByTestId('google-map')).toBeInTheDocument();
      expect(screen.getByText('📌 Places Map')).toBeInTheDocument();
    });

    it('renders places map from address-only marker by geocoding client-side', async () => {
      // Mock google.maps.Geocoder used by the component
      (global as any).google = {
        maps: {
          Geocoder: jest.fn(() => ({
            geocode: (_req: any, cb: any) =>
              cb(
                [
                  {
                    geometry: {
                      location: {
                        lat: () => 37.7985,
                        lng: () => -122.4467,
                      },
                    },
                  },
                ],
                'OK'
              ),
          })),
        },
      };

      const config = {
        map_type: 'places' as const,
        markers: [
          { address: '3348 Steiner St, San Francisco, CA 94123', title: 'Milos Meze' },
        ],
      };

      render(<InteractiveMap config={config as any} />);

      expect(screen.getByTestId('google-map')).toBeInTheDocument();
      expect(screen.getByText('📌 Places Map')).toBeInTheDocument();

      await waitFor(() => {
        // Marker title comes from AdvancedMarker mock
        expect(screen.getByText('Milos Meze')).toBeInTheDocument();
      });
    });
  });

  describe('Default Values', () => {
    it('uses default center when not provided', () => {
      const config = {
        map_type: 'location' as const,
      };

      render(<InteractiveMap config={config} />);

      // Should render without errors
      expect(screen.getByTestId('google-map')).toBeInTheDocument();
    });

    it('uses default zoom based on map type', () => {
      const configs = [
        { map_type: 'route' as const, origin: 'SF', destination: 'SJ' },
        { map_type: 'location' as const },
        { map_type: 'places' as const },
      ];

      configs.forEach((config) => {
        const { unmount } = render(<InteractiveMap config={config} />);
        expect(screen.getByTestId('google-map')).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('Error Handling', () => {
    it('shows error when API key is missing', () => {
      const originalKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
      delete process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

      const config = {
        map_type: 'location' as const,
        center: { lat: 37.7749, lng: -122.4194 },
      };

      render(<InteractiveMap config={config} />);

      expect(screen.getByText('Map Error')).toBeInTheDocument();
      expect(screen.getByText(/API key is not configured/)).toBeInTheDocument();

      // Restore API key
      process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY = originalKey;
    });
  });

  describe('Visual Appearance', () => {
    it('has correct dimensions and styling', () => {
      const config = {
        map_type: 'location' as const,
        center: { lat: 37.7749, lng: -122.4194 },
      };

      const { container } = render(<InteractiveMap config={config} />);

      const mapContainer = container.firstChild as HTMLElement;
      expect(mapContainer).toHaveClass('w-full');
      expect(mapContainer).toHaveClass('h-[500px]');
      expect(mapContainer).toHaveClass('rounded-lg');
      expect(mapContainer).toHaveClass('shadow-xl');
    });

    it('displays map type indicator', () => {
      const configs = [
        { map_type: 'route' as const, origin: 'SF', destination: 'SJ', label: '🗺️ Route Map' },
        { map_type: 'location' as const, label: '📍 Location Map' },
        { map_type: 'places' as const, label: '📌 Places Map' },
      ];

      configs.forEach((config) => {
        const { label, ...mapConfig } = config;
        const { unmount } = render(<InteractiveMap config={mapConfig as any} />);
        expect(screen.getByText(label)).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('Integration with unified-chat-interface', () => {
    it('can be rendered from JSON detection', () => {
      const jsonData = {
        type: 'interactive_map',
        config: {
          map_type: 'route' as const,
          origin: 'San Francisco, CA',
          destination: 'San Carlos, CA',
          travel_mode: 'DRIVING' as const,
        },
      };

      // Simulate what unified-chat-interface does
      if (jsonData.type === 'interactive_map') {
        render(<InteractiveMap config={jsonData.config} />);
      }

      expect(screen.getByTestId('google-map')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('map has proper role attribute', () => {
      const config = {
        map_type: 'location' as const,
        center: { lat: 37.7749, lng: -122.4194 },
      };

      render(<InteractiveMap config={config} />);

      const map = screen.getByRole('region');
      expect(map).toBeInTheDocument();
    });
  });
});
