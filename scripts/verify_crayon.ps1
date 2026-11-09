param([switch]$Render)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$cache = Join-Path $env:USERPROFILE '.gradle\caches\modules-2\files-2.1'
function Find-Jar([string]$module, [string]$version) {
    $path = Get-ChildItem -LiteralPath (Join-Path $cache "$module\$version") -Filter '*.jar' -Recurse | Select-Object -First 1 -ExpandProperty FullName
    if (-not $path) { throw "Missing cached $module $version; run the project dependency setup first." }
    return $path
}
$stdlib = Find-Jar 'org.jetbrains.kotlin\kotlin-stdlib' '2.1.20'
$junit = Find-Jar 'junit\junit' '4.13.2'
$hamcrest = Find-Jar 'org.hamcrest\hamcrest-core' '1.3'
$annotations = Find-Jar 'org.jetbrains\annotations' '13.0'
$compiler = @(
    (Find-Jar 'org.jetbrains.kotlin\kotlin-compiler-embeddable' '2.1.20'),
    $stdlib,
    (Find-Jar 'org.jetbrains.kotlin\kotlin-script-runtime' '2.1.20'),
    (Find-Jar 'org.jetbrains.kotlin\kotlin-daemon-embeddable' '2.1.20'),
    (Find-Jar 'org.jetbrains.intellij.deps\trove4j' '1.0.20200330'),
    (Find-Jar 'org.jetbrains.kotlinx\kotlinx-coroutines-core-jvm' '1.8.0'),
    $annotations
) -join ';'
$outDir = Join-Path $project 'build\crayon-verification'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$classPath = @($stdlib,$junit,$hamcrest,$annotations) -join ';'
$sources = @(
    (Join-Path $project 'app\src\main\java\com\bugworld\app\drawing\PaintDocument.kt'),
    (Join-Path $project 'app\src\main\java\com\bugworld\app\drawing\PaintGesture.kt'),
    (Join-Path $project 'app\src\test\java\com\bugworld\app\PngTestPixels.kt'),
    (Join-Path $project 'app\src\test\java\com\bugworld\app\PaintDocumentTest.kt')
)
if ($Render) { $sources += Join-Path $PSScriptRoot 'CrayonSamples.kt' }
& java -cp $compiler org.jetbrains.kotlin.cli.jvm.K2JVMCompiler -no-stdlib -no-reflect -jvm-target 11 -classpath $classPath -d (Join-Path $outDir 'classes') @sources
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& java -cp "$(Join-Path $outDir 'classes');$classPath" org.junit.runner.JUnitCore com.bugworld.app.PaintDocumentTest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($Render) {
    & java '-Djava.awt.headless=true' -cp "$(Join-Path $outDir 'classes');$classPath" CrayonSamplesKt (Join-Path $project 'docs\visual-redesign\2026-10-08\crayon-runtime-v2.png')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
