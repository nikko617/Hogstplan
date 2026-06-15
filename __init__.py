def classFactory(iface):
    from .hogstplan_plugin import HogstplanPlugin

    return HogstplanPlugin(iface)