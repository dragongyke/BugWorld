param([string]$RoutesPath,[switch]$CompileRuntime)
$ErrorActionPreference='Stop'
$project=Split-Path -Parent $PSScriptRoot
$cache='C:/Users/Admin/.gradle/caches/modules-2/files-2.1'
function Find-StageJar([string]$module,[string]$version) {
    $result=Get-ChildItem -LiteralPath "$cache/$module/$version" -Filter '*.jar' -Recurse | Select-Object -First 1 -ExpandProperty FullName
    if(-not $result) { throw "Missing cached $module/$version" }
    return $result
}
$stdlib=Find-StageJar 'org.jetbrains.kotlin/kotlin-stdlib' '2.1.20'
$junit=Find-StageJar 'junit/junit' '4.13.2'
$hamcrest=Find-StageJar 'org.hamcrest/hamcrest-core' '1.3'
$annotations=Find-StageJar 'org.jetbrains/annotations' '13.0'
$coroutines=Find-StageJar 'org.jetbrains.kotlinx/kotlinx-coroutines-core-jvm' '1.9.0'
$compiler=@((Find-StageJar 'org.jetbrains.kotlin/kotlin-compiler-embeddable' '2.1.20'),$stdlib,
    (Find-StageJar 'org.jetbrains.kotlin/kotlin-script-runtime' '2.1.20'),
    (Find-StageJar 'org.jetbrains.kotlin/kotlin-daemon-embeddable' '2.1.20'),
    (Find-StageJar 'org.jetbrains.intellij.deps/trove4j' '1.0.20200330'),$coroutines,$annotations) -join ';'
$outDir=Join-Path $project '.work/stage-optimization/kotlin'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$classPath=@($stdlib,$junit,$hamcrest,$annotations) -join ';'
$sources=@("$project/app/src/main/java/com/bugworld/app/garden/StageFrameStats.kt",
           "$project/app/src/test/java/com/bugworld/app/StageFrameStatsTest.kt")
& java -cp $compiler org.jetbrains.kotlin.cli.jvm.K2JVMCompiler -no-stdlib -no-reflect -jvm-target 11 -classpath $classPath -d "$outDir/classes" @sources
if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& java -cp "$outDir/classes;$classPath" org.junit.runner.JUnitCore com.bugworld.app.StageFrameStatsTest
if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if($RoutesPath) {
    $routeSources=@("$project/app/src/main/java/com/bugworld/app/data/Artwork.kt",
        "$project/app/src/main/java/com/bugworld/app/interaction/HandPoint.kt",
        "$project/app/src/main/java/com/bugworld/app/garden/NaturalMotion.kt",$RoutesPath,
        "$project/app/src/test/java/com/bugworld/app/ApprovedGardenRoutesTest.kt","$project/scripts/RouteSamples.kt")
    & java -cp $compiler org.jetbrains.kotlin.cli.jvm.K2JVMCompiler -no-stdlib -no-reflect -jvm-target 11 -classpath $classPath -d "$outDir/routes" @routeSources
    if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & java -cp "$outDir/routes;$classPath" org.junit.runner.JUnitCore com.bugworld.app.ApprovedGardenRoutesTest
    if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & java -cp "$outDir/routes;$classPath" RouteSamplesKt "$outDir/candidate-poses.csv"
    if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if($CompileRuntime) {
    # Read an existing integration output; write only this task's isolated compiler output.
    # GardenScene's Compose lowering and APK integration remain the integration build's responsibility.
    $appClasses="$project/app/build/tmp/kotlin-classes/debug"
    if(-not(Test-Path -LiteralPath $appClasses)) { throw 'No existing app classes for SDK API probe' }
    $runtimeCp=@($classPath,$coroutines,$appClasses,"$project/.work/v3-native-probe/core.jar",
        "$project/.work/v3-native-probe/native-foundation.jar",
        'C:/Users/Admin/AppData/Local/Android/Sdk/platforms/android-35/android.jar') -join ';'
    $runtimeSources=@("$project/app/src/main/java/com/bugworld/app/garden/StageFrameStats.kt",
        "$project/app/src/main/java/com/bugworld/app/garden/StageDiagnostics.kt",
        "$project/app/src/main/java/com/bugworld/app/garden/GardenRuntime.kt",
        "$project/app/src/main/java/com/bugworld/app/spatial/SceneLighting.kt")
    & java -cp $compiler org.jetbrains.kotlin.cli.jvm.K2JVMCompiler -no-stdlib -no-reflect -jvm-target 11 "-Xfriend-paths=$appClasses" -classpath $runtimeCp -d "$outDir/runtime-probe.jar" @runtimeSources
    if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Output 'Stage runtime SDK API probe passed (excludes Compose lowering/APK).'
}
