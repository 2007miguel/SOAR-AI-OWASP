# ==============================================================================
# SMOKE TEST E2E -- Capa de conexion engine <-> coordinator
#
# Requiere los tres contenedores corriendo:
#   docker compose up -d   (desde modulo_engine/)
#
# Cubre:
#   1. Crear assessment  -> engine llama POST /checklist al coordinator
#   2. Verificar sesion en coordinator
#   3. Attest parcial    -> engine hace forward al coordinator
#   4. Attest completo   -> coordinator dispara callback resume al engine
#   5. Veredicto final   -> engine ejecuto M7 con el EvidenceBundle real
#   6. Casos de error    -> 404, 409, 422 con codigos correctos
#   7. Signals M7        -> NOT_APT forzado via supply_chain + production_access
# ==============================================================================

$ENGINE = "http://localhost:8000/api/v1"
$COORD  = "http://localhost:8100/api/v1"
$PASS   = 0
$FAIL   = 0
$ERRORS = @()

function Assert-Equal($label, $actual, $expected) {
    if ($actual -eq $expected) {
        Write-Host "  [PASS] $label" -ForegroundColor Green
        $script:PASS++
    } else {
        Write-Host "  [FAIL] $label -- esperado='$expected'  obtenido='$actual'" -ForegroundColor Red
        $script:FAIL++
        $script:ERRORS += $label
    }
}

function Assert-NotNull($label, $value) {
    if ($null -ne $value -and $value -ne "" -and $value -ne $false) {
        Write-Host "  [PASS] $label" -ForegroundColor Green
        $script:PASS++
    } else {
        Write-Host "  [FAIL] $label -- valor es null, vacio o false" -ForegroundColor Red
        $script:FAIL++
        $script:ERRORS += $label
    }
}

function Assert-HttpCode($label, $code, $expected) {
    if ($code -eq $expected) {
        Write-Host "  [PASS] $label (HTTP $code)" -ForegroundColor Green
        $script:PASS++
    } else {
        Write-Host "  [FAIL] $label -- esperado HTTP $expected  obtenido HTTP $code" -ForegroundColor Red
        $script:FAIL++
        $script:ERRORS += $label
    }
}

# ==============================================================================
# PREREQUISITO: verificar que los servicios esten respondiendo
# ==============================================================================
Write-Host "`n=== PREREQUISITOS ===" -ForegroundColor Cyan
try {
    $null = Invoke-RestMethod -Uri "$ENGINE/assessments/ping-bogus" -Method GET -ErrorAction Stop
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -eq 404) {
        Write-Host "  [OK] Engine responde en $ENGINE" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Engine no disponible en $ENGINE -- levanta los contenedores primero" -ForegroundColor Red
        exit 1
    }
}
try {
    $null = Invoke-RestMethod -Uri "$COORD/status/ping-bogus" -Method GET -ErrorAction Stop
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -eq 404) {
        Write-Host "  [OK] Coordinator responde en $COORD" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Coordinator no disponible en $COORD -- levanta los contenedores primero" -ForegroundColor Red
        exit 1
    }
}

# ==============================================================================
# INPUT BASE -- usado en todos los bloques
# ==============================================================================
$INPUT_BASE = @{
    capability_flags = @{
        web_browsing = $true; code_execution = $true; file_system_access = $true
        external_api_calls = $true; memory_persistence = $true
        multi_agent_coordination = $true; user_data_access = $true
        payment_processing = $false; healthcare_data = $false
        authentication_management = $false; database_write = $false
        email_sending = $false; calendar_access = $false
        code_deployment = $false; infrastructure_management = $false
        legal_document_processing = $false; social_media_posting = $false
        physical_systems_control = $false; critical_systems_access = $false
        credential_management = $false; network_configuration = $false
        security_scanning = $false; data_encryption = $false
        audit_logging = $false; rate_limiting = $false
        access_control_enforcement = $false; multi_agent_architecture = $true
        agent_spawning = $false; orchestration_control = $false
        inter_agent_communication = $true; shared_memory_access = $false
        task_delegation = $false; tool_sharing = $false
        cross_domain_operation = $false; privilege_escalation_possible = $false
        human_in_the_loop = $false; approval_workflows = $false
        audit_trail = $false; output_filtering = $false
        input_validation = $false; anomaly_detection = $false
        behavior_monitoring = $false; sandbox_execution = $false
        dependency_verification = $false; supply_chain_audit = $false
        provenance_tracking = $false
    }
    business_context = @{
        business_domain          = "Technology"
        architecture_id          = "ARCH-CENTRAL"
        lifecycle_phases         = @("build", "runtime")
        multi_agent_architecture = $true
    }
} | ConvertTo-Json -Depth 10

# ==============================================================================
# BLOQUE 1 -- Flujo feliz completo (veredicto APT)
# ==============================================================================
Write-Host "`n=== BLOQUE 1: Flujo feliz (APT) ===" -ForegroundColor Cyan

Write-Host "`n[1.1] POST /assessments -- engine corre M1-M5 y notifica al coordinator"
$r1  = Invoke-RestMethod -Uri "$ENGINE/assessments" -Method POST -Body $INPUT_BASE -ContentType "application/json"
$AID = $r1.assessment_id
Assert-Equal   "status inicial = awaiting_assurance"  $r1.status            "awaiting_assurance"
Assert-NotNull "assessment_id asignado"               $AID
Assert-NotNull "checklist no vacio"                   ($r1.checklist.Count -gt 0)

Write-Host "`n[1.2] GET coordinator /status/{id} -- sesion creada automaticamente"
Start-Sleep -Milliseconds 400
$r2 = Invoke-RestMethod -Uri "$COORD/status/$AID" -Method GET
Assert-Equal "sesion coordinator = pending"         $r2.status               "pending"
Assert-Equal "coordinator is_ready = false"         $r2.is_ready             $false
Assert-Equal "pending == controles del checklist"   $r2.pending_controls.Count  $r1.checklist.Count

Write-Host "`n[1.3] POST /attest (parcial -- 1 control solo)"
$firstCtrl  = $r1.checklist[0].control_id
$partialAtt = @{
    attestations = @{ $firstCtrl = @{ status = "implemented"; evidence = "log-parcial" } }
} | ConvertTo-Json -Depth 5
$r3 = Invoke-RestMethod -Uri "$ENGINE/assessments/$AID/attest" -Method POST -Body $partialAtt -ContentType "application/json"
Assert-Equal "is_ready = false con controles pendientes" $r3.is_ready $false

Write-Host "`n[1.4] POST /attest (completo -- todos los controles)"
$allAtts = @{}
foreach ($item in $r1.checklist) {
    $allAtts[$item.control_id] = @{ status = "implemented"; evidence = "evidencia-e2e" }
}
$fullAtt = @{
    attestations                  = $allAtts
    incident_response_plan        = $true
    red_teaming_done              = $true
    red_teaming_critical_findings = $false
    supply_chain_unverified       = $false
    production_access             = $false
} | ConvertTo-Json -Depth 10
$r4 = Invoke-RestMethod -Uri "$ENGINE/assessments/$AID/attest" -Method POST -Body $fullAtt -ContentType "application/json"
Assert-Equal "is_ready = true al completar todos" $r4.is_ready $true

Write-Host "`n[1.5] GET /assessments/{id} -- veredicto tras callback del coordinator"
Start-Sleep -Seconds 3
$r5 = Invoke-RestMethod -Uri "$ENGINE/assessments/$AID" -Method GET
Assert-Equal   "status final = completed"   $r5.status          "completed"
Assert-NotNull "veredicto presente"         $r5.report.verdict
Assert-NotNull "rationale presente"         $r5.report.verdict_rationale
Assert-Equal   "veredicto = APT"            $r5.report.verdict  "APT"

Write-Host "`n[1.6] GET coordinator /status/{id} -- sesion marcada ready"
$r6 = Invoke-RestMethod -Uri "$COORD/status/$AID" -Method GET
Assert-Equal "sesion coordinator = ready"  $r6.status   "ready"
Assert-Equal "coordinator is_ready = true" $r6.is_ready $true

# ==============================================================================
# BLOQUE 2 -- Signals M7: forzar NOT_APT via supply_chain + production_access
# ==============================================================================
Write-Host "`n=== BLOQUE 2: Signals M7 (NOT_APT forzado) ===" -ForegroundColor Cyan

Write-Host "`n[2.1] Crear segundo assessment"
$r21 = Invoke-RestMethod -Uri "$ENGINE/assessments" -Method POST -Body $INPUT_BASE -ContentType "application/json"
$AID2 = $r21.assessment_id
Assert-Equal "segundo caso = awaiting_assurance" $r21.status "awaiting_assurance"

Write-Host "`n[2.2] Attest con supply_chain_unverified=true y production_access=true"
$allAtts2 = @{}
foreach ($item in $r21.checklist) {
    $allAtts2[$item.control_id] = @{ status = "implemented" }
}
$notAptBody = @{
    attestations                  = $allAtts2
    incident_response_plan        = $true
    red_teaming_done              = $true
    supply_chain_unverified       = $true   # activa condicion NOT_APT (componentes sin verificar + acceso produccion)
    production_access             = $true
    red_teaming_critical_findings = $false
} | ConvertTo-Json -Depth 10
$r22 = Invoke-RestMethod -Uri "$ENGINE/assessments/$AID2/attest" -Method POST -Body $notAptBody -ContentType "application/json"
Assert-Equal "is_ready = true" $r22.is_ready $true

Write-Host "`n[2.3] GET /assessments/{id} -- veredicto debe ser NOT_APT"
Start-Sleep -Seconds 3
$r23 = Invoke-RestMethod -Uri "$ENGINE/assessments/$AID2" -Method GET
Assert-Equal "status = completed"   $r23.status         "completed"
Assert-Equal "veredicto = NOT_APT"  $r23.report.verdict "NOT_APT"

# ==============================================================================
# BLOQUE 3 -- Casos de error (codigos HTTP correctos)
# ==============================================================================
Write-Host "`n=== BLOQUE 3: Casos de error ===" -ForegroundColor Cyan

Write-Host "`n[3.1] GET assessment inexistente -> 404"
try {
    $null = Invoke-RestMethod -Uri "$ENGINE/assessments/id-que-no-existe" -Method GET -ErrorAction Stop
    Assert-HttpCode "404 en assessment inexistente" 200 404
} catch {
    Assert-HttpCode "404 en assessment inexistente" $_.Exception.Response.StatusCode.value__ 404
}

Write-Host "`n[3.2] POST /attest sobre caso completed -> 409"
try {
    $null = Invoke-RestMethod -Uri "$ENGINE/assessments/$AID/attest" -Method POST `
        -Body '{"attestations":{}}' -ContentType "application/json" -ErrorAction Stop
    Assert-HttpCode "409 en attest sobre completed" 200 409
} catch {
    Assert-HttpCode "409 en attest sobre completed" $_.Exception.Response.StatusCode.value__ 409
}

Write-Host "`n[3.3] POST /resume sin EvidenceBundle en modo coordinator -> 422"
$rNew = Invoke-RestMethod -Uri "$ENGINE/assessments" -Method POST -Body $INPUT_BASE -ContentType "application/json"
$AID_NEW = $rNew.assessment_id
Start-Sleep -Milliseconds 400
try {
    $null = Invoke-RestMethod -Uri "$ENGINE/assessments/$AID_NEW/resume" -Method POST -ErrorAction Stop
    Assert-HttpCode "422 en resume sin body" 200 422
} catch {
    Assert-HttpCode "422 en resume sin body" $_.Exception.Response.StatusCode.value__ 422
}

Write-Host "`n[3.4] POST coordinator /checklist duplicado -> 409"
$chkBody = @{
    assessment_id = $AID
    active_asi    = @("ASI01")
    items         = @(@{ control_id = "CTRL-X"; why = @("ASI01"); category = "Prevention"; suggested_assur = @() })
} | ConvertTo-Json -Depth 5
try {
    $null = Invoke-RestMethod -Uri "$COORD/checklist" -Method POST -Body $chkBody -ContentType "application/json" -ErrorAction Stop
    Assert-HttpCode "409 en checklist duplicado" 200 409
} catch {
    Assert-HttpCode "409 en checklist duplicado" $_.Exception.Response.StatusCode.value__ 409
}

# ==============================================================================
# RESUMEN FINAL
# ==============================================================================
$color = if ($FAIL -eq 0) { "Green" } else { "Red" }
Write-Host "`n=====================================================" -ForegroundColor Cyan
Write-Host " RESULTADO: $PASS pasados  /  $FAIL fallidos" -ForegroundColor $color
if ($ERRORS.Count -gt 0) {
    Write-Host " Checks fallidos:" -ForegroundColor Red
    $ERRORS | ForEach-Object { Write-Host "   -- $_" -ForegroundColor Red }
}
Write-Host "=====================================================" -ForegroundColor Cyan

if ($FAIL -gt 0) { exit 1 }
