// GOATS RT Manager Android
//
// Plugin versions are resolved in settings.gradle.kts and are also written
// explicitly in fullapp/build.gradle.kts. Keeping the root build script free
// of plugin classpath declarations prevents the "plugin version missing" /
// "already on classpath" ambiguity when GitHub Actions builds the physical
// /fullapp module.
