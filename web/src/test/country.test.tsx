import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import i18n from '../i18n';
import type { CountryData } from '../lib/types';
import { CountryView } from '../pages/Country';
import sample from './country.sample.json';

const data = sample as CountryData;

// jsdom has no canvas or ResizeObserver; the chart layer is stubbed, the page is not.
vi.mock('../components/Chart', () => ({ Chart: ({ label }: { label: string }) => <div role="img" aria-label={label} /> }));

beforeAll(() => {
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

function renderCountry(tab?: 'summary' | 'composition' | 'seasonality' | 'trend') {
  return render(
    <MemoryRouter>
      <CountryView d={data} tab={tab} />
    </MemoryRouter>,
  );
}

describe('Country page', () => {
  afterEach(cleanup);

  it('renders the summary tab in English', async () => {
    await i18n.changeLanguage('en');
    renderCountry();
    for (const heading of ['The latest release', 'Against the target', 'Core and non-core', 'Contributions by item']) {
      expect(screen.getByRole('heading', { level: 2, name: heading })).toBeTruthy();
    }
    for (const tab of ['Summary', 'Composition', 'Seasonality', 'Trend & rates', 'Explore']) {
      expect(screen.getByRole('button', { name: tab })).toBeTruthy();
    }
    expect(screen.getByText('IPCA at 4.56% over 12 months')).toBeTruthy();
    expect(screen.getByText(/0.23 pp above the market median/)).toBeTruthy();
    expect(screen.getByRole('note').textContent).toMatch(/not real figures/);
  });

  it('renders the composition, seasonality and trend tabs', async () => {
    await i18n.changeLanguage('en');
    for (const [tab, headings] of [
      ['composition', ['Drivers', 'Recent months', 'Core and non-core', 'The basket', 'How widespread are increases?']],
      ['seasonality', ['This month against its seasonal pattern', 'What was unusual for the time of year', 'Seasonal profiles']],
      ['trend', ['Release details', 'Underlying trend', 'Next month', 'History', 'Policy and markets']],
    ] as const) {
      renderCountry(tab);
      for (const heading of headings) {
        expect(screen.getByRole('heading', { level: 2, name: heading })).toBeTruthy();
      }
      cleanup();
    }
  });

  it('splits the change between core and non-core on the composition tab', async () => {
    await i18n.changeLanguage('en');
    renderCountry('composition');
    expect(screen.getByRole('heading', { level: 3, name: 'How much came from core and from non-core' })).toBeTruthy();
    expect(screen.getByText(/The month \(December 2025\)/)).toBeTruthy();
    expect(screen.getAllByText('49%').length).toBeGreaterThan(0);
  });

  it('uses decimal commas and pt-BR labels in Portuguese', async () => {
    await i18n.changeLanguage('pt-BR');
    renderCountry();
    expect(screen.getByRole('heading', { level: 2, name: 'A última divulgação' })).toBeTruthy();
    expect(screen.getByText('IPCA em 4,56% em 12 meses')).toBeTruthy();
    expect(screen.getAllByText(/0,23 p\.p\./).length).toBeGreaterThan(0);
  });
});
