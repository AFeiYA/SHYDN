using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }
using { /UnrealEngine.com/Temporary/SpatialMath }

# 核心受损警报级别
alert_level := enum:
    Normal
    YellowAlert     # 血量 < 40%
    RedEmergency    # 血量 < 15%
    Destroyed       # 血量 <= 0

# 零号矩阵能量核心生命与警报控制器
core_health_device := class(creative_device):

    # 基础数值（严格遵循 GDD 数值规划）
    @editable var MaxCoreHealth : float = 30000.0
    @editable var MaxCoreShield : float = 10000.0
    @editable var ShieldRegenPerSecond : float = 500.0
    @editable var ShieldRegenDelay : float = 10.0

    # 关联装置
    @editable HudWarningMessage : ?hud_message_device = false
    @editable AlertAudioPlayer : ?audio_player_device = false
    @editable EndGameDevice : ?end_game_device = false

    # 运行时状态
    var CurrentHealth : float = 30000.0
    var CurrentShield : float = 10000.0
    var CurrentAlert : alert_level = alert_level.Normal
    var SecondsSinceLastHit : float = 0.0
    var IsCoreAlive : logic = true

    # 全局事件分发
    CoreDestroyedEvent<public> : event() = event(){}
    EmergencyAlertEvent<public> : event() = event(){}

    OnBegin<override>()<suspends> : void =
        set CurrentHealth = MaxCoreHealth
        set CurrentShield = MaxCoreShield
        set CurrentAlert = alert_level.Normal
        set IsCoreAlive = true
        Print("【零号矩阵核心】已上线！生命值: {CurrentHealth}/{MaxCoreHealth}, 护盾: {CurrentShield}/{MaxCoreShield}")
        
        # 启动护盾自愈与受击计时协程
        spawn{ RunShieldRegenLoop() }

    # 核心受损入口
    DamageCore<public>(Amount : float) : void =
        if (not IsCoreAlive?):
            return

        set SecondsSinceLastHit = 0.0
        var RemainingDamage : float = Amount

        # 1. 优先消耗护盾
        if (CurrentShield > 0.0):
            if (CurrentShield >= RemainingDamage):
                set CurrentShield -= RemainingDamage
                set RemainingDamage = 0.0
            else:
                set RemainingDamage -= CurrentShield
                set CurrentShield = 0.0

        # 2. 剩余伤害穿透至核心血量
        if (RemainingDamage > 0.0):
            set CurrentHealth -= RemainingDamage

        Print("【核心受击】当前生命: {CurrentHealth}/{MaxCoreHealth}, 护盾: {CurrentShield}/{MaxCoreShield}")
        EvaluateHealthState()

    # 评估当前血量危机状态并触发对应警报
    EvaluateHealthState() : void =
        HealthPercent := (CurrentHealth / MaxCoreHealth) * 100.0

        if (CurrentHealth <= 0.0):
            set CurrentHealth = 0.0
            set CurrentAlert = alert_level.Destroyed
            set IsCoreAlive = false
            HandleCoreDestroyed()
        else if (HealthPercent < 15.0):
            if (CurrentAlert <> alert_level.RedEmergency):
                set CurrentAlert = alert_level.RedEmergency
                TriggerRedEmergency()
        else if (HealthPercent < 40.0):
            if (CurrentAlert <> alert_level.YellowAlert and CurrentAlert <> alert_level.RedEmergency):
                set CurrentAlert = alert_level.YellowAlert
                TriggerYellowAlert()
        else:
            set CurrentAlert = alert_level.Normal

    # 黄色预警 (< 40%)
    TriggerYellowAlert() : void =
        Print("【黄色预警】核心生命值低于 40%！请注意清理走廊逼近怪潮！")
        if (Msg := HudWarningMessage?):
            Msg.SetText(StringToMessage("【黄色预警】核心血量 < 40%！注意防守！"))
            Msg.Show()
        if (Audio := AlertAudioPlayer?):
            Audio.Play()

    # 红色绝境 (< 15%)
    TriggerRedEmergency() : void =
        Print("【红色绝境】警告：能量核心生命值低于 15%！崩溃在即！全员立刻回防！")
        if (Msg := HudWarningMessage?):
            Msg.SetText(StringToMessage("【红色绝境】核心血量 < 15%！立刻回防！"))
            Msg.Show()
        if (Audio := AlertAudioPlayer?):
            Audio.Play()
        # 通知传送门等外部系统触发紧急召回通道
        EmergencyAlertEvent.Signal()

    # 核心摧毁
    HandleCoreDestroyed() : void =
        Print("【防线沦陷】零号矩阵核心被摧毁！游戏失败！")
        if (Msg := HudWarningMessage?):
            Msg.SetText(StringToMessage("【防线沦陷】零号矩阵已崩溃！"))
            Msg.Show()
        CoreDestroyedEvent.Signal()
        if (EndGame := EndGameDevice?):
            AllPlayers := GetPlayspace().GetPlayers()
            if (FirstPlayer := AllPlayers[0]):
                EndGame.Activate(FirstPlayer)

    # 护盾自然恢复循环 (脱战后恢复)
    RunShieldRegenLoop()<suspends> : void =
        loop:
            Sleep(1.0)
            if (not IsCoreAlive?):
                break

            set SecondsSinceLastHit += 1.0

            # 脱战指定秒数后开始回盾
            if (SecondsSinceLastHit >= ShieldRegenDelay and CurrentShield < MaxCoreShield):
                NewShield := CurrentShield + ShieldRegenPerSecond
                if (NewShield > MaxCoreShield):
                    set CurrentShield = MaxCoreShield
                else:
                    set CurrentShield = NewShield

    # 外部接口：维修核心生命
    RepairCore<public>(Amount : float) : void =
        if (not IsCoreAlive?):
            return
        set CurrentHealth = Min(MaxCoreHealth, CurrentHealth + Amount)
        EvaluateHealthState()
        Print("【核心维修】生命值已恢复至: {CurrentHealth}/{MaxCoreHealth}")

    # 外部接口：升级护盾上限
    UpgradeCoreShield<public>(BonusShield : float) : void =
        set MaxCoreShield += BonusShield
        set CurrentShield += BonusShield
        Print("【核心科技】护盾扩容成功！新护盾上限: {MaxCoreShield}")

    # 外部接口：查询当前是否处于濒死红色警报
    IsEmergencyState<public>()<transacts> : logic =
        if (CurrentAlert = alert_level.RedEmergency):
            return true
        return false

    StringToMessage<localizes>(Value : string) : message = "{Value}"
