/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  // Trailing slashes ensure each route gets its own directory with index.html
  trailingSlash: true,
};

export default nextConfig;
