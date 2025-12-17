/**
 * Markdown Rendering Tests
 *
 * Tests for ReactMarkdown configuration in UnifiedChatInterface
 * to ensure images from Google Maps Static API are rendered correctly.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';

// Custom sanitize schema (same as in UnifiedChatInterface)
const customSanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    img: [
      ...(defaultSchema.attributes?.img || []),
      ['src', /^https?:\/\//],
      'alt',
      'title',
      'width',
      'height',
      'loading',
      'className',
      'class'
    ],
  },
  protocols: {
    ...defaultSchema.protocols,
    src: ['http', 'https', 'data'],
  },
};

describe('Markdown Rendering', () => {
  describe('Image Rendering', () => {
    it('should render markdown images with Google Maps URLs', () => {
      const content = '![Route Map](https://maps.googleapis.com/maps/api/staticmap?size=600x400&key=TEST)';

      render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      const img = screen.getByRole('img');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', 'https://maps.googleapis.com/maps/api/staticmap?size=600x400&key=TEST');
      expect(img).toHaveAttribute('alt', 'Route Map');
    });

    it('should render markdown images with https URLs', () => {
      const content = '![Test Image](https://example.com/image.png)';

      render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      const img = screen.getByRole('img');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', 'https://example.com/image.png');
    });

    it('should render markdown images with http URLs', () => {
      const content = '![Test Image](http://example.com/image.png)';

      render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      const img = screen.getByRole('img');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', 'http://example.com/image.png');
    });

    it('should sanitize dangerous HTML while keeping images', () => {
      const content = '![Safe Image](https://example.com/image.png)<script>alert("xss")</script>';

      render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      const img = screen.getByRole('img');
      expect(img).toBeInTheDocument();

      // Script tag should be sanitized away
      const script = screen.queryByText(/alert/);
      expect(script).not.toBeInTheDocument();
    });
  });

  describe('Text Rendering', () => {
    it('should render plain text', () => {
      const content = 'Plain text message';

      const { container } = render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      expect(container).toHaveTextContent('Plain text message');
    });

    it('should render markdown with bold and italic', () => {
      const content = '**Bold text** and *italic text*';

      const { container } = render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      expect(container.querySelector('strong')).toHaveTextContent('Bold text');
      expect(container.querySelector('em')).toHaveTextContent('italic text');
    });

    it('should render markdown headings', () => {
      const content = '## Test Heading\n\nParagraph text';

      const { container } = render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      const heading = container.querySelector('h2');
      expect(heading).toBeInTheDocument();
      expect(heading).toHaveTextContent('Test Heading');
    });

    it('should render markdown lists', () => {
      const content = '- Item 1\n- Item 2\n- Item 3';

      const { container } = render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      const list = container.querySelector('ul');
      expect(list).toBeInTheDocument();
      const items = container.querySelectorAll('li');
      expect(items).toHaveLength(3);
      expect(items[0]).toHaveTextContent('Item 1');
    });

    it('should render markdown code blocks', () => {
      const content = '```python\nprint("hello")\n```';

      const { container } = render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      const code = container.querySelector('code');
      expect(code).toBeInTheDocument();
      expect(code).toHaveTextContent('print("hello")');
    });

    it('should render markdown links', () => {
      const content = '[Google Maps](https://maps.google.com)';

      render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', 'https://maps.google.com');
      expect(link).toHaveTextContent('Google Maps');
    });
  });

  describe('Complex Markdown', () => {
    it('should render markdown with image and text together', () => {
      const content = `Here is a visual map view:

![Route Map](https://maps.googleapis.com/maps/api/staticmap?size=600x400&key=TEST)

The route is approximately 23.9 miles.`;

      const { container } = render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      // Check image is present
      const img = screen.getByRole('img');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('alt', 'Route Map');

      // Check text is present
      expect(container).toHaveTextContent('Here is a visual map view:');
      expect(container).toHaveTextContent('The route is approximately 23.9 miles.');
    });

    it('should render MapAgent typical response', () => {
      const content = `Here is the visual map view for driving from San Francisco to San Carlos, CA:

![Route Map](https://maps.googleapis.com/maps/api/staticmap?size=600x400&maptype=roadmap&format=png&key=TEST&zoom=10&path=color:0x0000ff|weight:5|37.7749,-122.4194|37.5072,-122.2605)

The driving route from San Francisco, CA to San Carlos, CA is approximately:
- **Distance**: 23.9 miles (38.5 km)
- **Estimated Time**: 30 minutes

The main route follows US-101 S.`;

      const { container } = render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      // Check image
      const img = screen.getByRole('img');
      expect(img).toBeInTheDocument();
      expect(img.getAttribute('src')).toContain('maps.googleapis.com');
      expect(img.getAttribute('src')).toContain('path=');

      // Check bold text
      expect(container.querySelector('strong')).toBeInTheDocument();

      // Check all text content
      expect(container).toHaveTextContent('San Francisco');
      expect(container).toHaveTextContent('23.9 miles');
      expect(container).toHaveTextContent('30 minutes');
    });
  });

  describe('Schema Safety', () => {
    it('should block javascript: URLs in images', () => {
      const content = '![XSS](javascript:alert("xss"))';

      const { container } = render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      // Image should not be rendered with javascript: URL
      const img = container.querySelector('img');
      if (img) {
        expect(img.getAttribute('src')).not.toContain('javascript:');
      }
    });

    it('should block data: URLs with executable content', () => {
      const content = '![XSS](data:text/html,<script>alert("xss")</script>)';

      const { container } = render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[
            rehypeRaw,
            [rehypeSanitize, customSanitizeSchema],
          ]}
        >
          {content}
        </ReactMarkdown>
      );

      // Should not execute script
      const script = screen.queryByText(/alert/);
      expect(script).not.toBeInTheDocument();
    });
  });
});
