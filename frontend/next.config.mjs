/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.ytimg.com" },
      { protocol: "https", hostname: "**.tiktokcdn.com" },
      { protocol: "https", hostname: "**.tiktokcdn-us.com" },
      { protocol: "https", hostname: "**.twimg.com" },
      { protocol: "https", hostname: "**.fbcdn.net" },
      { protocol: "https", hostname: "**.cdninstagram.com" },
    ],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
