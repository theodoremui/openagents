/**
 * Tests for interactive map label rendering and auto-bounds functionality
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { InteractiveMap } from '@/components/interactive-map';

// Mock the @vis.gl/react-google-maps library
jest.mock('@vis.gl/react-google-maps', () => ({
  APIProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="api-provider">{children}</div>,
  Map: ({ children }: { children: React.ReactNode }) => <div data-testid="google-map">{children}</div>,
  AdvancedMarker: ({ children, title }: { children?: React.ReactNode; title?: string }) => (
    <div data-testid="advanced-marker" title={title}>
      {children}
    </div>
  ),
  Pin: () => <div data-testid="pin" />,
  useMap: () => ({
    fitBounds: jest.fn(),
  }),
  useMapsLibrary: () => null,
}));

// Mock google.maps
global.google = {
  maps: {
    LatLngBounds: jest.fn(() => ({
      extend: jest.fn(),
    })),
  },
} as any;

describe('InteractiveMap - Labels and Auto-Bounds', () => {
  beforeEach(() => {
    // Set up environment variable
    process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY = 'test-api-key';
  });

  it('should render marker labels for places map', () => {
    const config = {
      map_type: 'places' as const,
      center: { lat: 37.7749, lng: -122.4194 },
      zoom: 13,
      markers: [
        { lat: 37.7955, lng: -122.3988, title: 'Kokkari Estiatorio' },
        { lat: 37.8044, lng: -122.4101, title: 'North Beach Gyros' },
        { lat: 37.7684, lng: -122.4147, title: 'The Parthenon' },
      ],
    };

    render(<InteractiveMap config={config} />);

    // Check that marker labels are rendered
    expect(screen.getByText('Kokkari Estiatorio')).toBeInTheDocument();
    expect(screen.getByText('North Beach Gyros')).toBeInTheDocument();
    expect(screen.getByText('The Parthenon')).toBeInTheDocument();
  });

  it('should render correct number of markers with labels', () => {
    const config = {
      map_type: 'places' as const,
      markers: [
        { lat: 37.7955, lng: -122.3988, title: 'Restaurant 1' },
        { lat: 37.8044, lng: -122.4101, title: 'Restaurant 2' },
      ],
    };

    const { container } = render(<InteractiveMap config={config} />);

    // Check for pin components
    const pins = container.querySelectorAll('[data-testid="pin"]');
    expect(pins.length).toBe(2);

    // Check for labels
    expect(screen.getByText('Restaurant 1')).toBeInTheDocument();
    expect(screen.getByText('Restaurant 2')).toBeInTheDocument();
  });

  it('should render labels with proper styling classes', () => {
    const config = {
      map_type: 'places' as const,
      markers: [
        { lat: 37.7955, lng: -122.3988, title: 'Test Venue' },
      ],
    };

    render(<InteractiveMap config={config} />);

    const label = screen.getByText('Test Venue');
    expect(label).toHaveClass('bg-white/95');
    expect(label).toHaveClass('backdrop-blur-sm');
    expect(label).toHaveClass('shadow-lg');
    expect(label).toHaveClass('border-gray-200');
  });

  it('should truncate long venue names', () => {
    const longName = 'This is a very long restaurant name that should be truncated on the map';
    const config = {
      map_type: 'places' as const,
      markers: [
        { lat: 37.7955, lng: -122.3988, title: longName },
      ],
    };

    render(<InteractiveMap config={config} />);

    const label = screen.getByText(longName);
    expect(label).toHaveClass('truncate');
    expect(label).toHaveClass('max-w-[200px]');
  });

  it('should render location map marker with label', () => {
    const config = {
      map_type: 'location' as const,
      center: { lat: 37.7749, lng: -122.4194 },
      zoom: 14,
    };

    render(<InteractiveMap config={config} />);

    // Should render "Location" label
    expect(screen.getByText('Location')).toBeInTheDocument();
  });

  it('should not render labels for route maps', () => {
    const config = {
      map_type: 'route' as const,
      origin: 'San Francisco, CA',
      destination: 'Oakland, CA',
    };

    const { container } = render(<InteractiveMap config={config} />);

    // Route maps don't use AdvancedMarker with labels
    const markers = container.querySelectorAll('[data-testid="advanced-marker"]');
    expect(markers.length).toBe(0);
  });

  it('should render map type indicator', () => {
    const config = {
      map_type: 'places' as const,
      markers: [
        { lat: 37.7955, lng: -122.3988, title: 'Test' },
      ],
    };

    render(<InteractiveMap config={config} />);

    expect(screen.getByText('📌 Places Map')).toBeInTheDocument();
  });
});
