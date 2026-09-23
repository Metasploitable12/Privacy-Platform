export const metadata = {
  title: "Privacy Operations Platform",
  description: "Self-hosted privacy operations platform — Phase 1 scaffold",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, background: "#f7f8fa" }}>
        <nav
          style={{
            padding: "12px 24px",
            borderBottom: "1px solid #e2e4e8",
            background: "#fff",
            display: "flex",
            gap: 20,
          }}
        >
          <strong>Privacy Ops</strong>
          <a href="/">Dashboard</a>
          <a href="/ropa">Processing Activities</a>
        </nav>
        <main style={{ padding: 24 }}>{children}</main>
      </body>
    </html>
  );
}
