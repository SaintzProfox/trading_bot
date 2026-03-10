import './globals.css'

export const metadata = {
  title: 'GoldBot — XAUUSD Trading Dashboard',
  description: 'Production trading bot dashboard for Gold (XAUUSD) on HFM',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
      </head>
      <body style={{ margin: 0, padding: 0 }}>{children}</body>
    </html>
  )
}
