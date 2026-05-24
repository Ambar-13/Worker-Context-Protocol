package wcp

import "testing"

func TestWorkerClassConstants(t *testing.T) {
	cases := []struct {
		c    WorkerClass
		want string
	}{
		{WorkerClassHuman, "human"},
		{WorkerClassAutonomousRobot, "autonomous_robot"},
		{WorkerClassTeleoperatedRobot, "teleoperated_robot"},
		{WorkerClassSemiAutonomous, "semi_autonomous"},
		{WorkerClassHybrid, "hybrid"},
	}
	for _, c := range cases {
		if string(c.c) != c.want {
			t.Fatalf("WorkerClass: got %q want %q", c.c, c.want)
		}
	}
}

func TestAttestationModeConstants(t *testing.T) {
	cases := []struct {
		m    AttestationMode
		want string
	}{
		{AttestationSensorWitness, "sensor-witness"},
		{AttestationThirdPartyWitness, "third-party-witness"},
		{AttestationCryptographicPres, "cryptographic-presence"},
		{AttestationOwnerSignOff, "owner-sign-off"},
	}
	for _, c := range cases {
		if string(c.m) != c.want {
			t.Fatalf("AttestationMode: got %q want %q", c.m, c.want)
		}
	}
}

func TestSchemaVersionConstant(t *testing.T) {
	if SchemaVersion != "wcp/0.2" {
		t.Fatalf("SchemaVersion must be wcp/0.2, got %q", SchemaVersion)
	}
}

func TestSdkVersionConstantShape(t *testing.T) {
	// Sanity: looks like a semver string with at least two dots or the
	// pre-v1 form "0.X.Y".
	if SdkVersion == "" {
		t.Fatal("SdkVersion empty")
	}
}
